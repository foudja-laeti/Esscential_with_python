"""API FastAPI ; contrats HTTP conservés et documentation interactive /docs."""
import asyncio
import json
import re
from urllib.parse import parse_qs
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from fastapi.openapi.utils import get_openapi
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from .domain import ApiError, Store
from .models import MODELS
from .runtime import AsgiServer

MAX_BODY = 65_536
METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


def create_app(service, delay_ms=0, mode="normal"):
    if service not in ("users", "products", "orders"):
        raise ValueError("Service inconnu.")
    if type(delay_ms) is not int or not 0 <= delay_ms <= 30_000 or mode not in ("normal", "unavailable"):
        raise ValueError("Configuration de simulation invalide.")
    store = Store(service)
    prefix = "/api/" + service
    app = FastAPI(title="Service " + service, version="2.0.0", redirect_slashes=False)
    app.state.store = store

    def reply(request, status, body=None, headers=None):
        payload = b"" if body is None else json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
        fields = [("X-Service-Name", service), ("Cache-Control", "no-store")]
        if body is not None:
            fields.append(("Content-Type", "application/json; charset=utf-8"))
        if status != 204:
            fields.append(("Content-Length", str(len(payload))))
        fields.extend((headers or {}).items())
        response = Response(b"" if request.method == "HEAD" else payload, status_code=status)
        response.raw_headers = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in fields]
        return response

    @app.exception_handler(ApiError)
    async def api_error(request, error):
        return reply(request, error.status, {"error": {"code": error.code, "message": error.message}}, error.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return await api_error(request, ApiError(400, "VALIDATION_ERROR", "Données de requête invalides."))

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        code = "ROUTE_NOT_FOUND" if error.status_code == 404 else "METHOD_NOT_ALLOWED"
        return await api_error(request, ApiError(error.status_code, code, "Route ou méthode inconnue.", error.headers))

    @app.exception_handler(Exception)
    async def internal_error(request, error):
        return reply(request, 500, {"error": {"code": "INTERNAL_ERROR", "message": "Erreur interne du service."}})

    async def read_json(request, partial):
        if request.headers.get("transfer-encoding"):
            raise ApiError(400, "TRANSFER_ENCODING_UNSUPPORTED", "Envoyez Content-Length sans Transfer-Encoding.")
        lengths = request.headers.getlist("content-length")
        if len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,10}", lengths[0]):
            raise ApiError(411, "LENGTH_REQUIRED", "Un Content-Length unique est requis.")
        if int(lengths[0]) > MAX_BODY:
            raise ApiError(413, "BODY_TOO_LARGE", "Le corps dépasse 65536 octets.")
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "Content-Type doit être application/json.")
        try:
            async with asyncio.timeout(10):
                raw = bytearray()
                async for chunk in request.stream():
                    raw.extend(chunk)
                    if len(raw) > MAX_BODY:
                        raise ApiError(413, "BODY_TOO_LARGE", "Le corps dépasse 65536 octets.")
        except TimeoutError:
            raise ApiError(408, "REQUEST_TIMEOUT", "Délai de lecture du corps dépassé.") from None
        if len(raw) != int(lengths[0]):
            raise ApiError(400, "INVALID_JSON", "Corps incomplet.")
        try:
            def reject_constant(value):
                raise ValueError(value)
            body = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
        except (ValueError, UnicodeError, RecursionError):
            raise ApiError(400, "INVALID_JSON", "Le corps doit être un JSON UTF-8 valide.") from None
        try:
            MODELS[service][int(partial)].model_validate(body)
        except ValidationError:
            raise ApiError(400, "VALIDATION_ERROR", "Champs ou types invalides.") from None
        # Conserver les champs réellement fournis ; domain applique les valeurs par défaut.
        return body

    async def health(request: Request):
        return reply(request, 200, {"service": service, "status": "ok", "mode": mode, "delayMs": delay_ms})

    async def dispatch(request: Request):
        raw_path = request.scope.get("raw_path", request.url.path.encode()).decode("ascii")
        match = re.fullmatch(re.escape(prefix) + r"(?:/([1-9][0-9]{0,9}))?", raw_path)
        if not match:
            raise ApiError(404, "ROUTE_NOT_FOUND", "Route inconnue.")
        ident = int(match[1]) if match[1] else None
        methods = ("GET", "HEAD", "PATCH", "DELETE", "OPTIONS") if ident else ("GET", "HEAD", "POST", "OPTIONS")
        if request.method not in methods:
            raise ApiError(405, "METHOD_NOT_ALLOWED", "Méthode non autorisée.", {"Allow": ", ".join(methods)})
        if request.method == "OPTIONS":
            return reply(request, 204, headers={"Allow": ", ".join(methods)})
        if delay_ms:
            await asyncio.sleep(delay_ms / 1000)
        if mode == "unavailable":
            raise ApiError(503, "SERVICE_UNAVAILABLE", "Indisponibilité simulée du service.", {"Retry-After": "5"})
        if request.method in ("GET", "HEAD"):
            if ident:
                result = {"data": store.get(ident)}
            else:
                try:
                    query = parse_qs(request.scope["query_string"].decode("ascii"), keep_blank_values=True, max_num_fields=20)
                except ValueError:
                    raise ApiError(400, "VALIDATION_ERROR", "Trop de paramètres de recherche.") from None
                result = store.listing(query)
            return reply(request, 200, result)
        if request.method == "POST":
            row = store.create(await read_json(request, False))
            return reply(request, 201, {"data": row}, {"Location": f"{prefix}/{row['id']}"})
        if request.method == "PATCH":
            return reply(request, 200, {"data": store.update(ident, await read_json(request, True))})
        store.delete(ident)
        return reply(request, 204)

    app.add_api_route("/health", health, methods=["GET"], summary="État du service")
    app.add_api_route("/health", health, methods=["HEAD"], include_in_schema=False)
    # Une route OpenAPI par opération ; les modèles de corps sont ajoutés ci-dessous.
    for suffix, methods in [("", ["GET", "POST"]), ("/{ident}", ["GET", "PATCH", "DELETE"])]:
        for method in methods:
            app.add_api_route(prefix + suffix, dispatch, methods=[method],
                              name=service + suffix.replace("/", "_") + method,
                              status_code=201 if method == "POST" else 204 if method == "DELETE" else 200)
    app.add_api_route(prefix, dispatch, methods=METHODS, include_in_schema=False)
    app.add_api_route(prefix + "/{remaining:path}", dispatch, methods=METHODS, include_in_schema=False)

    def openapi():
        if app.openapi_schema is None:
            schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
            components = schema.setdefault("components", {}).setdefault("schemas", {})
            for partial, method, path in [(False, "post", prefix), (True, "patch", prefix + "/{ident}")]:
                model = MODELS[service][int(partial)]
                body_schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
                components.update(body_schema.pop("$defs", {}))
                components[model.__name__] = body_schema
                schema["paths"][path][method]["requestBody"] = {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/" + model.__name__}}}}
            for path, operations in schema["paths"].items():
                for operation in operations.values():
                    if "{ident}" in path:
                        operation["parameters"] = [{"name": "ident", "in": "path", "required": True, "schema": {"type": "integer", "minimum": 1}}]
                    operation.setdefault("responses", {})["400"] = {"description": "Erreur de validation au format métier"}
            query_names = ["page", "limit"] + (["status", "userId"] if service == "orders" else ["q"])
            schema["paths"][prefix]["get"]["parameters"] = [{"name": n, "in": "query", "schema": {"type": "string"}} for n in query_names]
            app.openapi_schema = schema
        return app.openapi_schema
    app.openapi = openapi
    return app


def create_server(service, host="127.0.0.1", port=0, delay_ms=0, mode="normal"):
    app = create_app(service, delay_ms, mode)
    server = AsgiServer(app, host, port)
    server.store = app.state.store
    return server
