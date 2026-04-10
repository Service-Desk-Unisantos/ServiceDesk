import json
import socketserver
import threading


# Conjunto compartilhado com assinantes TCP conectados.
assinantes = set()
assinantes_lock = threading.Lock()


def _remover_assinante(cliente_socket):
    with assinantes_lock:
        assinantes.discard(cliente_socket)


def _broadcast(payload):
    mensagem = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    with assinantes_lock:
        conexoes_ativas = list(assinantes)

    for cliente_socket in conexoes_ativas:
        try:
            cliente_socket.sendall(mensagem)
        except Exception:
            _remover_assinante(cliente_socket)


class NotificacaoTCPHandler(socketserver.StreamRequestHandler):
    # Protocolo simples por linha:
    # - {"acao": "publicar", "payload": {...}}
    # - {"acao": "inscrever"}
    def handle(self):
        primeira_linha = self.rfile.readline()
        if not primeira_linha:
            return

        try:
            envelope = json.loads(primeira_linha.decode("utf-8"))
        except json.JSONDecodeError:
            self.wfile.write(b'{"status":"erro","mensagem":"json invalido"}\n')
            return

        acao = envelope.get("acao")
        if acao == "publicar":
            _broadcast(envelope.get("payload", {}))
            self.wfile.write(b'{"status":"ok"}\n')
            return

        if acao == "inscrever":
            with assinantes_lock:
                assinantes.add(self.request)
            self.wfile.write(b'{"status":"inscrito"}\n')
            try:
                while self.rfile.readline():
                    continue
            finally:
                _remover_assinante(self.request)
            return

        self.wfile.write(b'{"status":"erro","mensagem":"acao invalida"}\n')


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with ThreadedTCPServer(("127.0.0.1", 8765), NotificacaoTCPHandler) as servidor:
        print("Servidor TCP ativo em 127.0.0.1:8765")
        servidor.serve_forever()


if __name__ == "__main__":
    main()
