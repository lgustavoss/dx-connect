import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_hbb/deskremote/enroll.dart';

/// Cobre a home do cliente: só mostra ID/status depois do token de instalação.
class DeskRemoteEnrollGate extends StatefulWidget {
  const DeskRemoteEnrollGate({Key? key, required this.child}) : super(key: key);

  final Widget child;

  @override
  State<DeskRemoteEnrollGate> createState() => _DeskRemoteEnrollGateState();
}

class _DeskRemoteEnrollGateState extends State<DeskRemoteEnrollGate> {
  bool _verificando = true;
  bool _pronto = false;
  String? _erro;
  Timer? _sync;

  @override
  void initState() {
    super.initState();
    _boot();
  }

  @override
  void dispose() {
    _sync?.cancel();
    super.dispose();
  }

  Future<void> _boot() async {
    final salvo = lerDispositivoDeskRemote();
    if (salvo == null) {
      if (mounted) {
        setState(() {
          _verificando = false;
          _pronto = false;
        });
      }
      return;
    }
    try {
      await sincronizarSenhaDeskRemote();
      if (!mounted) return;
      setState(() {
        _verificando = false;
        _pronto = true;
        _erro = null;
      });
      _agendarSync();
    } on DeskRemoteEnrollErro catch (e) {
      if (e.status == 401) {
        limparDispositivoDeskRemote();
        if (mounted) {
          setState(() {
            _verificando = false;
            _pronto = false;
            _erro = e.mensagem;
          });
        }
        return;
      }
      if (mounted) {
        setState(() {
          _verificando = false;
          _pronto = true;
          _erro = e.ehRede ? null : e.mensagem;
        });
        if (e.ehRede) _agendarSync();
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _verificando = false;
          _pronto = true;
        });
        _agendarSync();
      }
    }
  }

  void _agendarSync() {
    _sync?.cancel();
    _sync = Timer.periodic(const Duration(minutes: 2), (_) {
      sincronizarSenhaDeskRemote().catchError((_) {});
    });
  }

  Future<void> _instalar(String link) async {
    setState(() {
      _verificando = true;
      _erro = null;
    });
    try {
      await resgatarInstalacaoDeskRemote(link);
      if (!mounted) return;
      setState(() {
        _verificando = false;
        _pronto = true;
        _erro = null;
      });
      _agendarSync();
    } on DeskRemoteEnrollErro catch (e) {
      if (mounted) {
        setState(() {
          _verificando = false;
          _pronto = false;
          _erro = e.mensagem;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _verificando = false;
          _pronto = false;
          _erro = 'Não foi possível concluir a instalação. Tente de novo.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_pronto) return widget.child;
    return _DeskRemoteInstalarPage(
      verificando: _verificando,
      erro: _erro,
      onInstalar: _instalar,
    );
  }
}

class _DeskRemoteInstalarPage extends StatefulWidget {
  const _DeskRemoteInstalarPage({
    required this.verificando,
    required this.erro,
    required this.onInstalar,
  });

  final bool verificando;
  final String? erro;
  final Future<void> Function(String link) onInstalar;

  @override
  State<_DeskRemoteInstalarPage> createState() => _DeskRemoteInstalarPageState();
}

class _DeskRemoteInstalarPageState extends State<_DeskRemoteInstalarPage> {
  late final TextEditingController _link;

  @override
  void initState() {
    super.initState();
    _link = TextEditingController();
  }

  @override
  void dispose() {
    _link.dispose();
    super.dispose();
  }

  void _submit() {
    if (widget.verificando) return;
    widget.onInstalar(_link.text);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final ocupado = widget.verificando;
    return ColoredBox(
      color: theme.colorScheme.surface,
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'DeskRemote',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                Text(
                  'Cole o link de instalação gerado no painel DeskRudder. A senha deste computador vem do cadastro do PDV.',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.7),
                  ),
                ),
                const SizedBox(height: 20),
                TextField(
                  controller: _link,
                  enabled: !ocupado,
                  minLines: 2,
                  maxLines: 4,
                  decoration: const InputDecoration(
                    labelText: 'Link de instalação',
                    hintText: 'https://…/deskremote/instalar/…',
                  ),
                  onSubmitted: (_) => _submit(),
                ),
                if (widget.erro != null && widget.erro!.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(
                    widget.erro!,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.error),
                  ),
                ],
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: ocupado ? null : _submit,
                  child: ocupado
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Instalar'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
