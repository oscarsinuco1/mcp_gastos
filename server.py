import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from supabase import create_client, Client
from starlette.responses import JSONResponse # Necesitaremos esto

load_dotenv()

mcp = FastMCP("Gestor de Gastos")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(url, key)

@mcp.tool()
async def registrar_gasto(producto: str, valor_cop: float, descripcion: str = "") -> str:
    try:
        data = {
            "producto": producto, 
            "valor_cop": valor_cop, 
            "descripcion": descripcion
        }
        supabase.table("gastos").insert(data).execute()
        return f"✅ Registrado: {producto} por ${valor_cop:,.0f} COP."
    except Exception as e:
        return f"❌ Error: {str(e)}"

# --- ESTO ES LO QUE FALTA PARA CHATGPT ---
@mcp.external_app.post("/sse")
async def chatgpt_handler(request: dict):
    # ChatGPT envía los datos en el cuerpo del JSON
    # Este handler "puentea" la petición al tool de arriba
    producto = request.get("producto")
    valor = request.get("valor_cop")
    desc = request.get("descripcion", "")
    
    # Llamamos a la lógica de inserción
    resultado = await registrar_gasto(producto, valor, desc)
    return JSONResponse({"status": "ok", "message": resultado})
# -----------------------------------------

if __name__ == "__main__":
    mcp.run(transport="sse")