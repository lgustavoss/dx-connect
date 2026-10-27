import 'package:flutter/material.dart';
import 'package:flutter_hbb/common.dart';
import 'package:flutter_hbb/deskremote/sessao.dart';
import 'package:flutter_hbb/models/platform_model.dart';

/// Aba Vinculados: frota do DeskRudder (não os Favoritos locais do RustDesk).
class DeskRemoteVinculadosView extends StatefulWidget {
  const DeskRemoteVinculadosView({Key? key}) : super(key: key);

  @override
  State<DeskRemoteVinculadosView> createState() =>
      _DeskRemoteVinculadosViewState();
}

class _DeskRemoteVinculadosViewState extends State<DeskRemoteVinculadosView> {
  bool _carregando = true;
  String? _erro;
  List<DeskRemoteFrotaItem> _itens = const [];
  String? _conectandoId;
  String _busca = '';
  final _buscaCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  @override
  void dispose() {
    _buscaCtrl.dispose();
    super.dispose();
  }

  Future<void> _carregar() async {
    setState(() {
      _carregando = true;
      _erro = null;
    });
    try {
      final itens = await listarFrotaVinculadaDeskRemote();
      if (!mounted) return;
      setState(() {
        _itens = itens;
        _carregando = false;
      });
    } on DeskRemoteAuthErro catch (e) {
      if (!mounted) return;
      setState(() {
        _erro = e.mensagem;
        _carregando = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _erro = 'Não foi possível carregar a frota. Tente de novo.';
        _carregando = false;
      });
    }
  }

  List<DeskRemoteFrotaItem> get _filtrados {
    final q = _busca.trim().toLowerCase();
    if (q.isEmpty) return _itens;
    return _itens.where((item) {
      if (item.rotulo.toLowerCase().contains(q)) return true;
      if ((item.hostname ?? '').toLowerCase().contains(q)) return true;
      return item.rotulosVinculos.any((r) => r.toLowerCase().contains(q));
    }).toList();
  }

  Future<void> _conectar(DeskRemoteFrotaItem item) async {
    if (_conectandoId != null) return;
    setState(() => _conectandoId = item.rustdeskId);
    try {
      if (!item.idRepetido &&
          item.rotulo.isNotEmpty &&
          item.rotulo != item.rustdeskId) {
        await bind.mainSetPeerAlias(id: item.rustdeskId, alias: item.rotulo);
      }
      String? senha;
      if (!item.idRepetido && item.empresaId != null && item.pdvId != null) {
        senha = await senhaPdvDeskRemote(
          empresaId: item.empresaId!,
          pdvId: item.pdvId!,
        );
      }
      if (!mounted) return;
      await connect(
        context,
        item.rustdeskId,
        password: senha,
      );
    } finally {
      if (mounted) setState(() => _conectandoId = null);
    }
  }

  Color _corOnline(bool? online) {
    if (online == true) return const Color.fromARGB(255, 50, 190, 166);
    if (online == false) return const Color.fromARGB(255, 224, 79, 95);
    return Theme.of(context).hintColor;
  }

  String _statusOnline(bool? online) {
    if (online == true) return 'Online';
    if (online == false) return 'Offline';
    return 'Sem sinal';
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _buscaCtrl,
                  onChanged: (v) => setState(() => _busca = v),
                  style: const TextStyle(fontSize: 14),
                  decoration: InputDecoration(
                    isDense: true,
                    hintText: 'Buscar na frota',
                    prefixIcon: const Icon(Icons.search, size: 18),
                    suffixIcon: _busca.isEmpty
                        ? null
                        : IconButton(
                            tooltip: 'Limpar',
                            icon: const Icon(Icons.close, size: 16),
                            onPressed: () {
                              _buscaCtrl.clear();
                              setState(() => _busca = '');
                            },
                          ),
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 8,
                    ),
                    border: const OutlineInputBorder(),
                  ),
                ),
              ),
              IconButton(
                tooltip: 'Atualizar',
                onPressed: _carregando ? null : _carregar,
                icon: const Icon(Icons.refresh, size: 18),
              ),
            ],
          ),
        ),
        if (_erro != null && _itens.isNotEmpty) _avisoAtualizacao(),
        Expanded(child: _corpo()),
      ],
    );
  }

  Widget _avisoAtualizacao() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Expanded(
            child: Text(
              _erro!,
              style: TextStyle(
                fontSize: 12,
                color: Theme.of(context).colorScheme.error,
              ),
            ),
          ),
          TextButton(
            onPressed: _carregando ? null : _carregar,
            child: const Text('Tentar de novo'),
          ),
        ],
      ),
    );
  }

  Widget _corpo() {
    if (_carregando && _itens.isEmpty) {
      return const Center(child: CircularProgressIndicator(strokeWidth: 2));
    }
    if (_erro != null && _itens.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_erro!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              TextButton(onPressed: _carregar, child: const Text('Tentar de novo')),
            ],
          ),
        ),
      );
    }
    if (_itens.isEmpty) {
      return const Center(
        child: Text('Nenhum computador vinculado na frota.'),
      );
    }
    final lista = _filtrados;
    if (lista.isEmpty) {
      return const Center(child: Text('Nenhum resultado nesta busca.'));
    }
    return ListView.separated(
      itemCount: lista.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (context, i) => _linha(lista[i]),
    );
  }

  Widget _linha(DeskRemoteFrotaItem item) {
    final ocupado = _conectandoId == item.rustdeskId;
    final titleStyle = Theme.of(context).textTheme.titleSmall;
    final extra = item.idRepetido && item.rotulosVinculos.length > 1
        ? item.rotulosVinculos.join(' · ')
        : null;
    final sub = [
      if (extra != null) extra,
      if (item.hostname != null && item.hostname != item.rotulo) item.hostname!,
      _statusOnline(item.online),
    ].join(' · ');
    return ListTile(
      dense: true,
      leading: Icon(Icons.circle, size: 10, color: _corOnline(item.online)),
      title: Text(item.rotulo, style: titleStyle, overflow: TextOverflow.ellipsis),
      subtitle: Text(sub, overflow: TextOverflow.ellipsis),
      trailing: ocupado
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.chevron_right, size: 18),
      onTap: ocupado ? null : () => _conectar(item),
    );
  }
}
