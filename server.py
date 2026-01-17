import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from supabase import create_client, Client

load_dotenv()

# Inicializar FastMCP
# 'app' es el nombre estándar para despliegues web
mcp = FastMCP("Gestor de Gastos")

# Configuración de Supabase
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_ANON_KEY") # Usamos la Anon Key
supabase: Client = create_client(url, key)

@mcp.tool()
async def registrar_gasto(producto: str, valor_cop: float, descripcion: str = "") -> str:
    """
    Registra un nuevo gasto en pesos colombianos.
    """
    try:
        data = {
            "producto": producto, 
            "valor_cop": valor_cop, 
            "descripcion": descripcion
        }
        # Al no haber RLS, esto funcionará directo con la ANON_KEY
        supabase.table("gastos").insert(data).execute()
        
        return f"✅ Registrado: {producto} por ${valor_cop:,.0f} COP."
    except Exception as e:
        return f"❌ Error: {str(e)}"

if __name__ == "__main__":
    # Para despliegue público, usamos el transporte SSE
    # Esto levantará un servidor web en el puerto 8000
    mcp.run(transport="sse")