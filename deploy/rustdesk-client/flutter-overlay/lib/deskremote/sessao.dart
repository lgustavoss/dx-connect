import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_hbb/deskremote/enroll.dart';

/// Sessão do atendente compartilhada com o Electron
/// (`%APPDATA%/DeskRudder/deskremote-sessao.json`).
///
/// O arquivo guarda o mesmo JWT de acesso (e refresh) que o painel já
/// persiste em localStorage neste PC — não é um segredo extra. Só o
/// Electron (origem https do painel) e o DeskRemote leem este arquivo.
const kDeskRemoteApex = 'deskrudder.com.br';
const kDeskRemotePermissao = 'rustdesk.monitorar';

final _slugRe = RegExp(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$');
const _slugsReservados = {
  'www',
  'api',
  'mail',
  'ftp',
  'cdn',
  'static',
  'app',
  'admin',
  'status',
  'portal',
};

class DeskRemoteSessao {
  const DeskRemoteSessao({
    required this.slug,
    required this.accessToken,
    this.refreshToken,
    this.email,
  });

  final String slug;
  final String accessToken;
  final String? refreshToken;
  final String? email;

  Map<String, dynamic> toJson() => {
        'slug': slug,
        'access_token': accessToken,
        if (refreshToken != null && refreshToken!.isNotEmpty)
          'refresh_token': refreshToken,
        if (email != null && email!.isNotEmpty) 'email': email,
      };

  static DeskRemoteSessao? fromJson(Map<String, dynamic> json) {
    final slug = (json['slug'] ?? '').toString().trim().toLowerCase();
    final access = (json['access_token'] ?? '').toString().trim();
    if (!slugValido(slug) || access.isEmpty) return null;
    final refresh = (json['refresh_token'] ?? '').toString().trim();
    final email = (json['email'] ?? '').toString().trim();
    return DeskRemoteSessao(
      slug: slug,
      accessToken: access,
      refreshToken: refresh.isEmpty ? null : refresh,
      email: email.isEmpty ? null : email,
    );
  }
}

class DeskRemoteAuthErro implements Exception {
  DeskRemoteAuthErro(
    this.mensagem, {
    this.status,
    this.ehRede = false,
    this.naoTentarDeNovo = false,
  });
  final String mensagem;
  final int? status;
  final bool ehRede;
  final bool naoTentarDeNovo;

  /// Token inválido: apaga o arquivo. Rede / 5xx mantêm a sessão para tentar de novo.
  bool get deveDescartarSessao => !ehRede && status == 401;

  @override
  String toString() => mensagem;
}

bool slugValido(String slug) {
  final s = slug.trim().toLowerCase();
  return s.isNotEmpty && _slugRe.hasMatch(s) && !_slugsReservados.contains(s);
}

String pastaDeskRudderAppData() {
  final appData = Platform.environment['APPDATA'] ?? '';
  if (appData.isEmpty) {
    throw DeskRemoteAuthErro('Não foi possível achar a pasta do usuário.');
  }
  return '$appData${Platform.pathSeparator}DeskRudder';
}

File arquivoSessaoDeskRemote() {
  return File(
    '${pastaDeskRudderAppData()}${Platform.pathSeparator}deskremote-sessao.json',
  );
}

File arquivoContaElectron() {
  return File(
    '${pastaDeskRudderAppData()}${Platform.pathSeparator}config.json',
  );
}

String? lerSlugDoElectron() {
  try {
    final raw = arquivoContaElectron().readAsStringSync();
    final json = jsonDecode(raw);
    if (json is! Map) return null;
    final slug = (json['slug'] ?? '').toString().trim().toLowerCase();
    return slugValido(slug) ? slug : null;
  } catch (_) {
    return null;
  }
}

DeskRemoteSessao? lerSessaoDeskRemote() {
  try {
    final raw = arquivoSessaoDeskRemote().readAsStringSync();
    final json = jsonDecode(raw);
    if (json is! Map) return null;
    return DeskRemoteSessao.fromJson(Map<String, dynamic>.from(json));
  } catch (_) {
    return null;
  }
}

void gravarSessaoDeskRemote(DeskRemoteSessao sessao) {
  final file = arquivoSessaoDeskRemote();
  file.parent.createSync(recursive: true);
  file.writeAsStringSync('${jsonEncode(sessao.toJson())}\n');
}

void limparSessaoDeskRemote() {
  try {
    final file = arquivoSessaoDeskRemote();
    if (file.existsSync()) file.deleteSync();
  } catch (_) {}
}

/// API da instância: `https://api-{slug}.deskrudder.com.br/v1/...` (não o host do painel).
Uri urlApi(String slug, String caminho) {
  final path = caminho.startsWith('/') ? caminho : '/$caminho';
  return Uri.parse('https://api-$slug.$kDeskRemoteApex/v1$path');
}

bool temPermissaoAcessoRemoto(Map<String, dynamic> me) {
  final role = (me['role'] ?? '').toString();
  if (role == 'saas_ops') return false;
  if (role == 'admin') return true;
  final perms = me['permissoes'];
  if (perms is List) {
    return perms.contains('admin') || perms.contains(kDeskRemotePermissao);
  }
  return false;
}

Future<Map<String, dynamic>> _lerJsonHttp(
  HttpClientResponse res,
) async {
  final text = await res.transform(utf8.decoder).join();
  if (text.isEmpty) return <String, dynamic>{};
  final decoded = jsonDecode(text);
  if (decoded is Map<String, dynamic>) return decoded;
  if (decoded is Map) return Map<String, dynamic>.from(decoded);
  return <String, dynamic>{};
}

String _mensagemHttp(int status, Map<String, dynamic> body) {
  final detail = (body['detail'] ?? '').toString().trim();
  if (status == 401) {
    return detail.isNotEmpty ? detail : 'E-mail ou senha inválidos';
  }
  if (status == 429) {
    return 'Muitas tentativas. Espere um pouco e tente de novo.';
  }
  if (detail.isNotEmpty) return detail;
  return 'Não foi possível entrar. Tente de novo.';
}

Future<Map<String, dynamic>> _httpJson({
  required Uri uri,
  required String method,
  Map<String, dynamic>? body,
  String? bearer,
}) async {
  final client = HttpClient();
  client.connectionTimeout = const Duration(seconds: 20);
  client.userAgent = 'DeskRemote/2.3.0';
  try {
    final req = method == 'GET'
        ? await client.getUrl(uri)
        : await client.postUrl(uri);
    req.headers.set(HttpHeaders.acceptHeader, 'application/json');
    if (bearer != null && bearer.isNotEmpty) {
      req.headers.set(HttpHeaders.authorizationHeader, 'Bearer $bearer');
    }
    if (body != null) {
      req.headers.contentType = ContentType.json;
      req.write(jsonEncode(body));
    }
    final res = await req.close().timeout(const Duration(seconds: 25));
    final json = await _lerJsonHttp(res);
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw DeskRemoteAuthErro(
        _mensagemHttp(res.statusCode, json),
        status: res.statusCode,
      );
    }
    return json;
  } on DeskRemoteAuthErro {
    rethrow;
  } on SocketException {
    throw DeskRemoteAuthErro(
      'Sem conexão com a internet. Verifique a rede e tente de novo.',
      ehRede: true,
    );
  } on HandshakeException {
    throw DeskRemoteAuthErro(
      'Não foi possível conectar na conta. Confira o identificador.',
      ehRede: true,
    );
  } on TimeoutException {
    throw DeskRemoteAuthErro(
      'Sem conexão com a internet. Verifique a rede e tente de novo.',
      ehRede: true,
    );
  } on HttpException {
    throw DeskRemoteAuthErro(
      'Sem conexão com a internet. Verifique a rede e tente de novo.',
      ehRede: true,
    );
  } catch (e) {
    if (e is DeskRemoteAuthErro) rethrow;
    throw DeskRemoteAuthErro(
      'Não foi possível entrar. Tente de novo.',
      ehRede: true,
    );
  } finally {
    client.close(force: true);
  }
}

Future<DeskRemoteSessao> loginDeskRemote({
  required String slug,
  required String email,
  required String senha,
}) async {
  final s = slug.trim().toLowerCase();
  if (!slugValido(s)) {
    throw DeskRemoteAuthErro(
      'Conta inválida. Use o identificador do endereço do painel (ex.: minhaempresa).',
    );
  }
  final mail = email.trim().toLowerCase();
  if (mail.isEmpty || senha.isEmpty) {
    throw DeskRemoteAuthErro('Informe o e-mail e a senha.');
  }
  final json = await _httpJson(
    uri: urlApi(s, '/auth/login'),
    method: 'POST',
    body: {'email': mail, 'senha': senha},
  );
  final access = (json['access_token'] ?? '').toString().trim();
  if (access.isEmpty) {
    throw DeskRemoteAuthErro('Não foi possível entrar. Tente de novo.');
  }
  if (json['must_change_password'] == true) {
    throw DeskRemoteAuthErro(
      'Altere a senha no DeskRudder antes de usar o DeskRemote.',
    );
  }
  final refresh = (json['refresh_token'] ?? '').toString().trim();
  return DeskRemoteSessao(
    slug: s,
    accessToken: access,
    refreshToken: refresh.isEmpty ? null : refresh,
    email: mail,
  );
}

Future<Map<String, dynamic>> meDeskRemote(DeskRemoteSessao sessao) {
  return _httpJson(
    uri: urlApi(sessao.slug, '/atendentes/me'),
    method: 'GET',
    bearer: sessao.accessToken,
  );
}

Future<DeskRemoteSessao?> renovarSessaoDeskRemote(DeskRemoteSessao sessao) async {
  final refresh = (sessao.refreshToken ?? '').trim();
  if (refresh.isEmpty) return null;
  try {
    final json = await _httpJson(
      uri: urlApi(sessao.slug, '/auth/refresh'),
      method: 'POST',
      body: {'refresh_token': refresh},
    );
    final access = (json['access_token'] ?? '').toString().trim();
    if (access.isEmpty) return null;
    final novoRefresh = (json['refresh_token'] ?? '').toString().trim();
    return DeskRemoteSessao(
      slug: sessao.slug,
      accessToken: access,
      refreshToken: novoRefresh.isEmpty ? refresh : novoRefresh,
      email: sessao.email,
    );
  } catch (_) {
    return null;
  }
}

/// Mesmo formato de `rotuloSessaoVinculo` no painel (`acessoRemotoUrl.mjs`).
/// Ex.: Posto Farol · SERVIDOR 001
String rotuloSessaoVinculo(Map<String, dynamic> vinculo) {
  final rotulo = (vinculo['rotulo_nome'] ?? '').toString().trim();
  final nome = rotulo.isEmpty ? 'Equipamento' : rotulo;
  final codigo = (vinculo['pdv_codigo'] ?? '').toString().trim();
  final base = codigo.isEmpty ? nome : '$nome $codigo';
  final rede = (vinculo['rede_nome'] ?? '').toString().trim();
  return rede.isEmpty ? base : '$rede · $base';
}

String _soDigitosId(String id) => id.replaceAll(RegExp(r'\D'), '');

class DeskRemoteFrotaItem {
  const DeskRemoteFrotaItem({
    required this.rustdeskId,
    required this.rotulo,
    this.online,
    this.hostname,
    this.empresaId,
    this.pdvId,
    this.idRepetido = false,
    this.rotulosVinculos = const [],
  });

  final String rustdeskId;
  final String rotulo;
  final bool? online;
  final String? hostname;
  final int? empresaId;
  final int? pdvId;
  final bool idRepetido;
  final List<String> rotulosVinculos;
}

Future<Map<String, dynamic>> _listarPeersVinculados(DeskRemoteSessao s) {
  return _httpJson(
    uri: urlApi(s.slug, '/rustdesk/peers').replace(
      queryParameters: const {'filtro': 'vinculado'},
    ),
    method: 'GET',
    bearer: s.accessToken,
  );
}

DeskRemoteFrotaItem? _itemDaFrota(Map<String, dynamic> peer) {
  final id = _soDigitosId((peer['rustdesk_id'] ?? '').toString());
  if (id.isEmpty) return null;
  final vinculos = peer['vinculos'];
  final rotulos = <String>[];
  int? empresaId;
  int? pdvId;
  if (vinculos is List) {
    for (final raw in vinculos) {
      if (raw is! Map) continue;
      final mapa = Map<String, dynamic>.from(raw);
      final nome = rotuloSessaoVinculo(mapa).trim();
      if (nome.isNotEmpty) rotulos.add(nome);
    }
    if (vinculos.length == 1 && vinculos.first is Map) {
      final unico = Map<String, dynamic>.from(vinculos.first as Map);
      empresaId = int.tryParse((unico['empresa_id'] ?? '').toString());
      pdvId = int.tryParse((unico['pdv_id'] ?? '').toString());
    }
  }
  final hostname = (peer['hostname'] ?? '').toString().trim();
  final repetido = peer['id_repetido'] == true ||
      (vinculos is List && vinculos.length > 1);
  // ID em vários PDVs: não inventar um rótulo único (o do primeiro PDV).
  final rotulo = repetido
      ? (hostname.isEmpty ? 'Computador em vários PDVs' : hostname)
      : (rotulos.isEmpty
          ? (hostname.isEmpty ? id : hostname)
          : rotulos.first);
  return DeskRemoteFrotaItem(
    rustdeskId: id,
    rotulo: rotulo,
    online: peer['online'] is bool ? peer['online'] as bool : null,
    hostname: hostname.isEmpty ? null : hostname,
    empresaId: empresaId,
    pdvId: pdvId,
    idRepetido: repetido,
    rotulosVinculos: rotulos,
  );
}

/// Frota do sistema (PDVs vinculados). Exige sessão DeskRudder.
Future<List<DeskRemoteFrotaItem>> listarFrotaVinculadaDeskRemote() async {
  final inicial = lerSessaoDeskRemote();
  if (inicial == null) {
    throw DeskRemoteAuthErro('Entre com a conta DeskRudder para ver a frota.');
  }
  DeskRemoteSessao sessao = inicial;
  Map<String, dynamic> json;
  try {
    json = await _listarPeersVinculados(sessao);
  } on DeskRemoteAuthErro catch (e) {
    if (e.status != 401) rethrow;
    final nova = await renovarSessaoDeskRemote(sessao);
    if (nova == null) rethrow;
    gravarSessaoDeskRemote(nova);
    sessao = nova;
    json = await _listarPeersVinculados(sessao);
  }
  final items = json['items'];
  if (items is! List) return const [];
  final out = <DeskRemoteFrotaItem>[];
  for (final raw in items) {
    if (raw is! Map) continue;
    final item = _itemDaFrota(Map<String, dynamic>.from(raw));
    if (item != null) out.add(item);
  }
  return out;
}

/// Senha do cadastro do PDV. 404/403 = sem senha ou sem permissão.
Future<String?> senhaPdvDeskRemote({
  required int empresaId,
  required int pdvId,
}) async {
  final inicial = lerSessaoDeskRemote();
  if (inicial == null) return null;
  Future<String?> pedir(DeskRemoteSessao s) async {
    try {
      final json = await _httpJson(
        uri: urlApi(s.slug, '/empresas/$empresaId/pdvs/$pdvId/credencial'),
        method: 'GET',
        bearer: s.accessToken,
      );
      final senha = (json['acesso_remoto_senha'] ?? '').toString().trim();
      return senha.isEmpty ? null : senha;
    } on DeskRemoteAuthErro catch (e) {
      if (e.status == 401) rethrow;
      return null;
    }
  }

  try {
    return await pedir(inicial);
  } on DeskRemoteAuthErro catch (e) {
    if (e.status != 401) return null;
    final nova = await renovarSessaoDeskRemote(inicial);
    if (nova == null) return null;
    gravarSessaoDeskRemote(nova);
    try {
      return await pedir(nova);
    } catch (_) {
      return null;
    }
  } catch (_) {
    return null;
  }
}

/// Rótulo do vínculo na frota (um PDV). Sem sessão, sem permissão ou ID
/// repetido: `null` — a aba cai no alias/`name=` ou em usuário@host.
Future<String?> buscarRotuloVinculoDeskRemote(String rustdeskId) async {
  final alvo = _soDigitosId(rustdeskId);
  if (alvo.isEmpty) return null;
  final inicial = lerSessaoDeskRemote();
  if (inicial == null) return null;

  try {
    return await () async {
      // Tipo não nulo aqui: o Dart não promove `DeskRemoteSessao?` capturado
      // num closure (o build 2.1.1 falhou nisso).
      DeskRemoteSessao sessao = inicial;
      Map<String, dynamic> json;
      try {
        json = await _listarPeersVinculados(sessao);
      } on DeskRemoteAuthErro catch (e) {
        if (e.status != 401) return null;
        final nova = await renovarSessaoDeskRemote(sessao);
        if (nova == null) return null;
        gravarSessaoDeskRemote(nova);
        sessao = nova;
        json = await _listarPeersVinculados(sessao);
      }
      final items = json['items'];
      if (items is! List) return null;
      for (final raw in items) {
        if (raw is! Map) continue;
        final peer = Map<String, dynamic>.from(raw);
        if (_soDigitosId((peer['rustdesk_id'] ?? '').toString()) != alvo) {
          continue;
        }
        final vinculos = peer['vinculos'];
        if (vinculos is! List || vinculos.length != 1) return null;
        final primeiro = vinculos.first;
        if (primeiro is! Map) return null;
        final rotulo =
            rotuloSessaoVinculo(Map<String, dynamic>.from(primeiro)).trim();
        return rotulo.isEmpty ? null : rotulo;
      }
      return null;
    }()
        // A aba da sessão é outro engine: o título só entra nos params da janela.
        .timeout(const Duration(seconds: 5), onTimeout: () => null);
  } catch (_) {
    return null;
  }
}

Future<Map<String, dynamic>> _lerConfiguracaoServidor(DeskRemoteSessao s) {
  return _httpJson(
    uri: urlApi(s.slug, '/rustdesk/configuracao'),
    method: 'GET',
    bearer: s.accessToken,
  );
}

Future<void> _aplicarServidorComSessao(DeskRemoteSessao sessao) async {
  final json = await _lerConfiguracaoServidor(sessao);
  if (json['configurado'] != true) {
    throw DeskRemoteAuthErro(
      'Acesso remoto não configurado nesta conta.',
      naoTentarDeNovo: true,
    );
  }
  final servidorId = (json['servidor_id'] ?? '').toString().trim();
  final relay = (json['servidor_relay'] ?? '').toString().trim();
  final chave = (json['chave'] ?? '').toString().trim();
  if (servidorId.isEmpty || chave.isEmpty) {
    throw DeskRemoteAuthErro(
      'Acesso remoto não configurado nesta conta.',
      naoTentarDeNovo: true,
    );
  }
  await aplicarServidorDeskRemote(
    servidorId: servidorId,
    relay: relay.isEmpty ? servidorId : relay,
    chave: chave,
  );
}

/// Grava o hbbs/hbbr da instância (não o servidor compilado no binário).
///
/// [silencioso] (`--connect` sem sessão, ou falha de rede): segue com o último
/// servidor gravado neste PC. No login da home, deixe `false` para avisar.
Future<void> aplicarServidorDaContaDeskRemote({bool silencioso = false}) async {
  final inicial = lerSessaoDeskRemote();
  if (inicial == null) {
    if (silencioso) return;
    throw DeskRemoteAuthErro(
      'Entre com a conta DeskRudder para definir o servidor de acesso remoto.',
    );
  }
  try {
    await _aplicarServidorComSessao(inicial);
  } on DeskRemoteAuthErro catch (e) {
    if (e.status == 401) {
      final nova = await renovarSessaoDeskRemote(inicial);
      if (nova != null) {
        gravarSessaoDeskRemote(nova);
        try {
          await _aplicarServidorComSessao(nova);
          return;
        } on DeskRemoteAuthErro {
          if (silencioso) return;
          rethrow;
        }
      }
    }
    if (silencioso) return;
    rethrow;
  }
}
