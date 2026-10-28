import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_hbb/deskremote/sessao.dart';

/// Cobre a home do atendente: Recentes e Conectar só com sessão DeskRudder.
/// `--connect` / `deskrudder://` do painel abre a janela da sessão à parte
/// (de propósito — o atendente já autenticou no painel).
class DeskRemoteAuthGate extends StatefulWidget {
  const DeskRemoteAuthGate({Key? key, required this.child}) : super(key: key);

  final Widget child;

  @override
  State<DeskRemoteAuthGate> createState() => _DeskRemoteAuthGateState();
}

class _DeskRemoteAuthGateState extends State<DeskRemoteAuthGate> {
  bool _verificando = true;
  bool _autenticado = false;
  String? _erro;
  Timer? _poll;
  /// Sair nesta janela não herda de novo o Electron até reabrir o app.
  bool _naoHerdarAposSair = false;

  @override
  void initState() {
    super.initState();
    _tentarSessaoSalva();
    _poll = Timer.periodic(const Duration(seconds: 2), (_) {
      if (!mounted || _autenticado || _verificando || _naoHerdarAposSair) {
        return;
      }
      if (lerSessaoDeskRemote() != null) {
        _tentarSessaoSalva();
      }
    });
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _tentarSessaoSalva() async {
    setState(() {
      _verificando = true;
      _erro = null;
    });
    var sessao = lerSessaoDeskRemote();
    if (sessao == null) {
      if (mounted) {
        setState(() {
          _verificando = false;
          _autenticado = false;
        });
      }
      return;
    }
    try {
      final me = await meDeskRemote(sessao);
      if (me['must_change_password'] == true) {
        limparSessaoDeskRemote();
        if (mounted) {
          setState(() {
            _verificando = false;
            _autenticado = false;
            _erro =
                'Altere a senha no DeskRudder antes de usar o DeskRemote.';
          });
        }
        return;
      }
      if (!temPermissaoAcessoRemoto(me)) {
        limparSessaoDeskRemote();
        if (mounted) {
          setState(() {
            _verificando = false;
            _autenticado = false;
            _erro = 'Sua conta não tem permissão para o acesso remoto.';
          });
        }
        return;
      }
      await aplicarServidorDaContaDeskRemote();
      if (mounted) {
        setState(() {
          _verificando = false;
          _autenticado = true;
          _erro = null;
        });
      }
    } on DeskRemoteAuthErro catch (e) {
      if (e.naoTentarDeNovo) {
        _pararPoll();
        if (mounted) {
          setState(() {
            _verificando = false;
            _autenticado = false;
            _erro = e.mensagem;
          });
        }
        return;
      }
      if (!e.ehRede) {
        final renovada = await renovarSessaoDeskRemote(sessao);
        if (renovada != null) {
          try {
            final me = await meDeskRemote(renovada);
            if (me['must_change_password'] == true) {
              limparSessaoDeskRemote();
              throw DeskRemoteAuthErro(
                'Altere a senha no DeskRudder antes de usar o DeskRemote.',
              );
            }
            if (temPermissaoAcessoRemoto(me)) {
              gravarSessaoDeskRemote(renovada);
              await aplicarServidorDaContaDeskRemote();
              if (mounted) {
                setState(() {
                  _verificando = false;
                  _autenticado = true;
                  _erro = null;
                });
              }
              return;
            }
            limparSessaoDeskRemote();
            if (mounted) {
              setState(() {
                _verificando = false;
                _autenticado = false;
                _erro = 'Sua conta não tem permissão para o acesso remoto.';
              });
            }
            return;
          } on DeskRemoteAuthErro catch (e2) {
            if (e2.naoTentarDeNovo) {
              _pararPoll();
            }
            if (e2.deveDescartarSessao) {
              limparSessaoDeskRemote();
            }
            if (mounted) {
              setState(() {
                _verificando = false;
                _autenticado = false;
                _erro = e2.mensagem;
              });
            }
            return;
          } catch (_) {
            if (mounted) {
              setState(() {
                _verificando = false;
                _autenticado = false;
              });
            }
            return;
          }
        }
      }
      if (e.deveDescartarSessao) {
        limparSessaoDeskRemote();
      }
      if (mounted) {
        setState(() {
          _verificando = false;
          _autenticado = false;
          _erro = e.mensagem;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _verificando = false;
          _autenticado = false;
        });
      }
    }
  }

  Future<void> _entrar({
    required String slug,
    required String email,
    required String senha,
  }) async {
    setState(() {
      _verificando = true;
      _erro = null;
    });
    try {
      final sessao = await loginDeskRemote(
        slug: slug,
        email: email,
        senha: senha,
      );
      final me = await meDeskRemote(sessao);
      if (me['must_change_password'] == true) {
        throw DeskRemoteAuthErro(
          'Altere a senha no DeskRudder antes de usar o DeskRemote.',
        );
      }
      if (!temPermissaoAcessoRemoto(me)) {
        throw DeskRemoteAuthErro(
          'Sua conta não tem permissão para o acesso remoto.',
        );
      }
      gravarSessaoDeskRemote(sessao);
      await aplicarServidorDaContaDeskRemote();
      if (mounted) {
        setState(() {
          _verificando = false;
          _autenticado = true;
          _erro = null;
        });
      }
    } on DeskRemoteAuthErro catch (e) {
      if (e.naoTentarDeNovo) {
        _pararPoll();
      }
      if (mounted) {
        setState(() {
          _verificando = false;
          _autenticado = false;
          _erro = e.mensagem;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _verificando = false;
          _autenticado = false;
          _erro = 'Não foi possível entrar. Tente de novo.';
        });
      }
    }
  }

  void _pararPoll() {
    _poll?.cancel();
    _poll = null;
  }

  void _sair() {
    // DeskRemote: Sair explícito — não relogar pelo poll da sessão do Electron.
    _naoHerdarAposSair = true;
    _pararPoll();
    limparSessaoDeskRemote();
    setState(() {
      _autenticado = false;
      _verificando = false;
      _erro = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_autenticado) {
      return Stack(
        children: [
          widget.child,
          Positioned(
            right: 12,
            bottom: 10,
            child: TextButton(
              onPressed: _sair,
              child: const Text('Sair'),
            ),
          ),
        ],
      );
    }
    return _DeskRemoteLoginPage(
      verificando: _verificando,
      erro: _erro,
      slugInicial: lerSlugDoElectron() ?? '',
      onEntrar: _entrar,
    );
  }
}

class _DeskRemoteLoginPage extends StatefulWidget {
  const _DeskRemoteLoginPage({
    required this.verificando,
    required this.erro,
    required this.slugInicial,
    required this.onEntrar,
  });

  final bool verificando;
  final String? erro;
  final String slugInicial;
  final Future<void> Function({
    required String slug,
    required String email,
    required String senha,
  }) onEntrar;

  @override
  State<_DeskRemoteLoginPage> createState() => _DeskRemoteLoginPageState();
}

class _DeskRemoteLoginPageState extends State<_DeskRemoteLoginPage> {
  late final TextEditingController _slug;
  late final TextEditingController _email;
  late final TextEditingController _senha;
  bool _mostrarSenha = false;

  @override
  void initState() {
    super.initState();
    _slug = TextEditingController(text: widget.slugInicial);
    _email = TextEditingController();
    _senha = TextEditingController();
  }

  @override
  void didUpdateWidget(covariant _DeskRemoteLoginPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.slugInicial.isNotEmpty && _slug.text.trim().isEmpty) {
      _slug.text = widget.slugInicial;
    }
  }

  @override
  void dispose() {
    _slug.dispose();
    _email.dispose();
    _senha.dispose();
    super.dispose();
  }

  void _submit() {
    if (widget.verificando) return;
    widget.onEntrar(
      slug: _slug.text,
      email: _email.text,
      senha: _senha.text,
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final ocupado = widget.verificando;
    return ColoredBox(
      color: theme.colorScheme.surface,
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 380),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: AutofillGroup(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'DeskRemote',
                    textAlign: TextAlign.center,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Entre com a mesma conta do DeskRudder.',
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.7),
                    ),
                  ),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _slug,
                    enabled: !ocupado,
                    textInputAction: TextInputAction.next,
                    autocorrect: false,
                    decoration: const InputDecoration(
                      labelText: 'Conta',
                      hintText: 'minhaempresa',
                      helperText: 'O identificador do painel (antes de .deskrudder.com.br)',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _email,
                    enabled: !ocupado,
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.username],
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(
                      labelText: 'E-mail',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _senha,
                    enabled: !ocupado,
                    obscureText: !_mostrarSenha,
                    autofillHints: const [AutofillHints.password],
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _submit(),
                    decoration: InputDecoration(
                      labelText: 'Senha',
                      suffixIcon: IconButton(
                        tooltip: _mostrarSenha ? 'Ocultar senha' : 'Mostrar senha',
                        onPressed: ocupado
                            ? null
                            : () => setState(() => _mostrarSenha = !_mostrarSenha),
                        icon: Icon(
                          _mostrarSenha
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined,
                        ),
                      ),
                    ),
                  ),
                  if ((widget.erro ?? '').isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text(
                      widget.erro!,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.error,
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  FilledButton(
                    onPressed: ocupado ? null : _submit,
                    child: ocupado
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Entrar'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
