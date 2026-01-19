import os
import uvicorn
from mcp.types import Tool
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
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
        Tool(
            name="registrar_gasto",
            description="Registra un gasto en pesos colombianos",
            inputSchema={
                "type": "object",
                "properties": {
                    "producto": {"type": "string"},
                    "valor_cop": {"type": "number"},
                    "descripcion": {"type": "string"}
                },
                "required": ["producto", "valor_cop"]
            }
        )
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
    try:
        body = await request.json()
        # Soporta tanto {"params": {...}} como {...}
        args = body.get("params", body)
        res = await handle_call_tool("registrar_gasto", args)
        return JSONResponse({"status": "ok", "message": res[0]["text"]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

# 4. Configuración de Rutas y App Starlette
# 4. Configuración de Rutas y App Starlette
sse = SseServerTransport("/messages")

async def handle_sse(request: Request):
    # El transporte necesita el scope y los canales de envío/recepción
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream, mcp.create_initialization_options())

# Esta es la ruta que suele dar el 401 si no está bien mapeada
async def handle_messages(request: Request):
    # Importante: Pasar los argumentos en el orden correcto para Starlette
    await sse.handle_post_messages(request.scope, request.receive, request._send)

app = Starlette(
    debug=True, # Importante para ver el error real si falla
    routes=[
        Route("/sse", endpoint=handle_sse), # GET por defecto
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
        Route("/chatgpt", endpoint=chatgpt_handler, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    import sys
    import asyncio

    # Si Gemini pasa 'stdio', solo arranca el modo flujo de texto
    if len(sys.argv) > 1 and sys.argv[1] == "stdio":
        from mcp.server.stdio import stdio_server
        
        async def run_stdio():
            # Importante: No imprimir nada antes o durante esto
            async with stdio_server() as (read_stream, write_stream):
                await mcp.run(
                    read_stream, 
                    write_stream, 
                    mcp.create_initialization_options()
                )
        
        try:
            asyncio.run(run_stdio())
        except Exception:
            pass # Evita que errores de salida ensucien el cierre
    else:
        # Modo Web para Render/ChatGPT
        import uvicorn
        port = int(os.environ.get("PORT", 8001))
        uvicorn.run(app, host="0.0.0.0", port=port)