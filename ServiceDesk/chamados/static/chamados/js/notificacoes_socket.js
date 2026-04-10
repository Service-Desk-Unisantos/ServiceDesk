(() => {
    // Usa configuracao global definida no template para URL do servidor socket.
    const socketUrl = window.SOCKET_NOTIFICACAO_URL || "ws://127.0.0.1:8765";
    // Dados do usuario atual para filtrar notificacoes destinadas a ele.
    const usuarioLogadoId = Number(window.USUARIO_LOGADO_ID || 0);
    const usuarioEhAdmin = Boolean(window.USUARIO_EH_ADMIN);
    const caixaNotificacoes = document.getElementById("caixa-notificacoes");

    // Sai silenciosamente se a pagina nao tiver area de notificacao configurada.
    if (!caixaNotificacoes) {
        return;
    }

    function deveExibir(payload) {
        // Admin pode enxergar todas as notificacoes; cliente so as proprias.
        if (usuarioEhAdmin) {
            return true;
        }
        return Number(payload.usuario_id) === usuarioLogadoId;
    }

    function renderizarNotificacao(texto) {
        // Cria alerta Bootstrap simples para exibir mensagem em tempo real.
        const notificacao = document.createElement("div");
        notificacao.className = "alert alert-info shadow-sm mb-2";
        notificacao.textContent = texto;
        caixaNotificacoes.prepend(notificacao);

        // Remove automaticamente apos alguns segundos para nao poluir a tela.
        setTimeout(() => {
            notificacao.remove();
        }, 6000);
    }

    function iniciarConexao() {
        // Conecta com o servidor socket local.
        const socket = new WebSocket(socketUrl);

        socket.onmessage = (event) => {
            let payload;
            try {
                // Espera JSON enviado pelo Django via servidor socket.
                payload = JSON.parse(event.data);
            } catch (_) {
                // Se vier texto puro, exibe diretamente.
                renderizarNotificacao(String(event.data));
                return;
            }

            // Filtra por usuario antes de renderizar notificacao.
            if (deveExibir(payload) && payload.mensagem) {
                renderizarNotificacao(payload.mensagem);
            }
        };

        socket.onclose = () => {
            // Reconecta automaticamente para manter notificacao ativa.
            setTimeout(iniciarConexao, 2000);
        };

        socket.onerror = () => {
            // Em caso de erro, fecha para acionar fluxo de reconexao.
            socket.close();
        };
    }

    // Inicia processo de conexao assim que script carregar.
    iniciarConexao();
})();
