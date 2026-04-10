import asyncio

import websockets


# Conjunto compartilhado com todos os clientes WebSocket conectados.
clientes_conectados = set()


async def broadcast(mensagem):
    # Envia a mesma mensagem para todos os clientes conectados (broadcast simples).
    if not clientes_conectados:
        return

    conexoes_ativas = set(clientes_conectados)
    for cliente in conexoes_ativas:
        try:
            await cliente.send(mensagem)
        except Exception:
            # Remove conexoes quebradas para manter o servidor estavel.
            clientes_conectados.discard(cliente)


async def tratar_cliente(websocket):
    # Registra cliente novo no conjunto global.
    clientes_conectados.add(websocket)
    try:
        # Recebe mensagens vindas de qualquer cliente e replica para todos.
        async for mensagem in websocket:
            await broadcast(mensagem)
    finally:
        # Remove cliente ao desconectar para evitar referencias antigas.
        clientes_conectados.discard(websocket)


async def main():
    # Sobe servidor local em porta fixa para facilitar testes academicos.
    async with websockets.serve(tratar_cliente, "127.0.0.1", 8765):
        print("Servidor socket ativo em ws://127.0.0.1:8765")
        await asyncio.Future()


if __name__ == "__main__":
    # Ponto de entrada simples para executar com: python server_socket.py
    asyncio.run(main())
