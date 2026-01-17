import os
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
from starlette.requests import Request
from supabase import create_client, Client

load_dotenv()

# 1. Configuración de Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

# 2. Configuración del Servidor MCP
mcp = Server("Gestor de Gastos")

@mcp.list_tools()
async def handle_list_tools():
    return [
        {
            "name": "registrar_gasto",
            "description": "Registra un gasto en pesos colombianos",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "producto": {"type": "string"},
                    "valor_cop": {"type": "number"},
                    "descripcion": {"type": "string"}
                },
                "required": ["producto", "valor_cop"]
            }
        }
    ]

@mcp.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    if name == "registrar_gasto":
        producto = arguments.get("producto")
        valor = arguments.get("valor_cop")
        desc = arguments.get("descripcion", "")
        
        try:
            supabase.table("gastos").insert({
                "producto": producto,
                "valor_cop": valor,
                "descripcion": desc
            }).execute()
            return [{"type": "text", "text": f"✅ Registrado: {producto} por ${valor:,.0f} COP."}]
        except Exception as e:
            return [{"type": "text", "text": f"❌ Error: {str(e)}"}]

# 3. Adaptador para ChatGPT (Endpoint POST normal)
async def chatgpt_handler(request: Request):
    body = await request.json()
    # Ejecutamos la misma lógica que el tool
    res = await handle_call_tool("registrar_gasto", body.get("params", {}))
    return JSONResponse({"status": "ok", "message": res[0]["text"]})

# 4. Configuración de Rutas y App Starlette
sse = SseServerTransport("/messages")

async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream, mcp.create_initialization_options())

app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse), # Para Clientes MCP
        Route("/messages", endpoint=sse.handle_post_message), # Requerido por MCP SSE
        Route("/chatgpt", endpoint=chatgpt_handler, methods=["POST"]), # Para ChatGPT
    ]
)

if __name__ == "__main__":
    import uvicorn
    # Escuchamos en el puerto que asigne Render o el 8000 local
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)