import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_hbb/models/platform_model.dart';

/// Instalação do DeskRemote cliente: token, servidor da instância e senha do painel.
const kDeskRemoteApex = 'deskrudder.com.br';

class DeskRemoteEnrollErro implements Exception {
  DeskRemoteEnrollErro(this.mensagem, {this.status, this.ehRede = false});
  final String mensagem;
  final int? status;
  final bool ehRede;

  @override
  String toString() => mensagem;
}

class LinkInstalacaoDeskRemote {
  const LinkInstalacaoDeskRemote({required this.apiBase, required this.token});
  final Uri apiBase;
  final String token;
}

class DispositivoDeskRemote {
  const DispositivoDeskRemote({
    required this.apiBase,
    required this.token,
    this.senhaVersao = 0,
    this.rustdeskId,
  });

  final Uri apiBase;
  final String token;
  final int senhaVersao;
  final String? rustdeskId;

  Map<String, dynamic> toJson() => {
        'api_base': apiBase.toString(),
        'token': token,
        'senha_versao': senhaVersao,
        if (rustdeskId != null && rustdeskId!.isNotEmpty) 'rustdesk_id': rustdeskId,
      };

  static DispositivoDeskRemote? fromJson(Map<String, dynamic> json) {
    final api = Uri.tryParse((json['api_base'] ?? '').toString().trim());
    final token = (json['token'] ?? '').toString().trim();
    if (api == null || api.host.isEmpty || token.isEmpty) return null;
    final versao = json['senha_versao'];
    return DispositivoDeskRemote(
      apiBase: api,
      token: token,
      senhaVersao: versao is int ? versao : int.tryParse('$versao') ?? 0,
      rustdeskId: (json['rustdesk_id'] ?? '').toString().trim().isEmpty
          ? null
          : (json['rustdesk_id'] ?? '').toString().trim(),
    );
  }
}

File arquivoDispositivoDeskRemote() {
  final appData = Platform.environment['APPDATA'] ?? '';
  if (appData.isEmpty) {
    throw DeskRemoteEnrollErro('Não foi possível achar a pasta do usuário.');
  }
  return File('$appData${Platform.pathSeparator}DeskRudder${Platform.pathSeparator}deskremote-dispositivo.json');
}

DispositivoDeskRemote? lerDispositivoDeskRemote() {
  try {
    final raw = arquivoDispositivoDeskRemote().readAsStringSync();
    final json = jsonDecode(raw);
    if (json is! Map) return null;
    return DispositivoDeskRemote.fromJson(Map<String, dynamic>.from(json));
  } catch (_) {
    return null;
  }
}

void gravarDispositivoDeskRemote(DispositivoDeskRemote row) {
  final file = arquivoDispositivoDeskRemote();
  file.parent.createSync(recursive: true);
  file.writeAsStringSync('${jsonEncode(row.toJson())}\n');
}

void limparDispositivoDeskRemote() {
  try {
    final file = arquivoDispositivoDeskRemote();
    if (file.existsSync()) file.deleteSync();
  } catch (_) {}
}

LinkInstalacaoDeskRemote? parseLinkInstalacaoDeskRemote(String bruto) {
  final text = bruto.trim();
  if (text.isEmpty) return null;
  final uri = Uri.tryParse(text);
  if (uri == null || uri.host.isEmpty) return null;
  final segs = uri.pathSegments.where((s) => s.isNotEmpty).toList();
  final i = segs.indexOf('instalar');
  if (i < 0 || i + 1 >= segs.length) return null;
  final token = segs[i + 1];
  if (token.isEmpty) return null;
  final host = uri.host.toLowerCase();
  if (host == 'localhost' || host == '127.0.0.1') {
    return LinkInstalacaoDeskRemote(
      apiBase: Uri.parse('http://127.0.0.1:8000'),
      token: token,
    );
  }
  final apiHost = host.startsWith('api-')
      ? host
      : (host.endsWith('.$kDeskRemoteApex') ? 'api-${host.split('.').first}.$kDeskRemoteApex' : host);
  return LinkInstalacaoDeskRemote(
    apiBase: Uri.parse('${uri.scheme}://$apiHost'),
    token: token,
  );
}

Uri _urlApi(Uri apiBase, String caminho) {
  final path = caminho.startsWith('/') ? caminho : '/$caminho';
  return apiBase.replace(path: '/v1$path');
}

Future<Map<String, dynamic>> _lerJsonHttp(HttpClientResponse res) async {
  final text = await res.transform(utf8.decoder).join();
  if (text.isEmpty) return <String, dynamic>{};
  final decoded = jsonDecode(text);
  if (decoded is Map<String, dynamic>) return decoded;
  if (decoded is Map) return Map<String, dynamic>.from(decoded);
  return <String, dynamic>{};
}

String _mensagemHttp(int status, Map<String, dynamic> body) {
  final detail = (body['detail'] ?? '').toString().trim();
  if (detail.isNotEmpty) return detail;
  if (status == 429) return 'Muitas tentativas. Espere um pouco e tente de novo.';
  return 'Não foi possível concluir a instalação. Tente de novo.';
}

Future<Map<String, dynamic>> _httpJson({
  required Uri uri,
  required String method,
  Map<String, dynamic>? body,
  String? bearer,
}) async {
  final client = HttpClient();
  client.connectionTimeout = const Duration(seconds: 20);
  client.userAgent = 'DeskRemote/2.0.0';
  try {
    final req = method == 'GET' ? await client.getUrl(uri) : await client.postUrl(uri);
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
      throw DeskRemoteEnrollErro(_mensagemHttp(res.statusCode, json), status: res.statusCode);
    }
    return json;
  } on DeskRemoteEnrollErro {
    rethrow;
  } on SocketException {
    throw DeskRemoteEnrollErro('Sem conexão com a internet. Verifique a rede e tente de novo.', ehRede: true);
  } on HandshakeException {
    throw DeskRemoteEnrollErro('Não foi possível conectar no painel. Confira o link.', ehRede: true);
  } on TimeoutException {
    throw DeskRemoteEnrollErro('Sem conexão com a internet. Verifique a rede e tente de novo.', ehRede: true);
  } on HttpException {
    throw DeskRemoteEnrollErro('Sem conexão com a internet. Verifique a rede e tente de novo.', ehRede: true);
  } catch (e) {
    if (e is DeskRemoteEnrollErro) rethrow;
    throw DeskRemoteEnrollErro('Não foi possível concluir a instalação. Tente de novo.', ehRede: true);
  } finally {
    client.close(force: true);
  }
}

Future<void> aplicarServidorDeskRemote({
  required String servidorId,
  required String relay,
  required String chave,
}) async {
  if (servidorId.isEmpty || chave.isEmpty) return;
  final atualId = (await bind.mainGetLocalOption(key: 'custom-rendezvous-server')).trim();
  final atualRelay = (await bind.mainGetLocalOption(key: 'relay-server')).trim();
  final atualChave = (await bind.mainGetLocalOption(key: 'key')).trim();
  final mudou = atualId != servidorId || atualRelay != relay || atualChave != chave;
  await bind.mainSetLocalOption(key: 'custom-rendezvous-server', value: servidorId);
  await bind.mainSetLocalOption(key: 'relay-server', value: relay);
  await bind.mainSetLocalOption(key: 'key', value: chave);
  // O binário Flutter nasce sem hbbs real; sem reiniciar o serviço o
  // mediador continua no placeholder e a home fica em «Conectando…».
  var precisa = mudou;
  if (!precisa) {
    precisa = !await _servidorDeskRemotePronto();
  }
  if (precisa) await _reconectarServidorDeskRemote();
}

Future<bool> _servidorDeskRemotePronto() async {
  try {
    final decoded = jsonDecode(await bind.mainGetConnectStatus());
    return decoded is Map && decoded['status_num'] == 1;
  } catch (_) {
    return false;
  }
}

Future<void> _reconectarServidorDeskRemote() async {
  try {
    await bind.mainStopService();
  } catch (_) {}
  try {
    await bind.mainStartService();
  } catch (_) {}
  for (var i = 0; i < 20; i++) {
    await Future<void>.delayed(const Duration(milliseconds: 300));
    if (await _servidorDeskRemotePronto()) return;
  }
}

Future<void> travarSenhaPermanenteDeskRemote() async {
  // O painel manda: senha permanente, sem uso único neste computador.
  await bind.mainSetOption(key: 'verification-method', value: 'use-permanent-password');
}

/// RustDesk 1.5.0 só expõe `mainSetPermanentPasswordWithResult` (não `mainSetPermanentPassword`).
Future<void> _gravarSenhaPermanenteDeskRemote(String senha) async {
  final ok = await bind.mainSetPermanentPasswordWithResult(password: senha);
  if (!ok) {
    throw DeskRemoteEnrollErro('Não foi possível gravar a senha neste computador. Tente de novo.');
  }
}

Future<void> aplicarServidorESenhaDeskRemote({
  required String servidorId,
  required String relay,
  required String chave,
  required String senha,
}) async {
  await aplicarServidorDeskRemote(servidorId: servidorId, relay: relay, chave: chave);
  await travarSenhaPermanenteDeskRemote();
  await _gravarSenhaPermanenteDeskRemote(senha);
}

Future<String> idLocalDeskRemote() async {
  final id = await bind.mainGetMyId();
  return id.toString().trim();
}

Future<DispositivoDeskRemote> resgatarInstalacaoDeskRemote(String bruto) async {
  final link = parseLinkInstalacaoDeskRemote(bruto);
  if (link == null) {
    throw DeskRemoteEnrollErro('Cole o link completo gerado no painel.');
  }
  final json = await _httpJson(
    uri: _urlApi(link.apiBase, '/deskremote/enroll'),
    method: 'POST',
    body: {'token': link.token},
  );
  final deviceToken = (json['dispositivo_token'] ?? '').toString().trim();
  if (deviceToken.isEmpty) {
    throw DeskRemoteEnrollErro('Não foi possível concluir a instalação. Tente de novo.');
  }
  final servidor = json['servidor'];
  final mapa = servidor is Map ? Map<String, dynamic>.from(servidor) : <String, dynamic>{};
  final senha = (json['senha'] ?? '').toString();
  await aplicarServidorESenhaDeskRemote(
    servidorId: (mapa['servidor_id'] ?? '').toString(),
    relay: (mapa['servidor_relay'] ?? '').toString(),
    chave: (mapa['chave'] ?? '').toString(),
    senha: senha,
  );
  var rustdeskId = '';
  for (var i = 0; i < 30; i++) {
    rustdeskId = await idLocalDeskRemote();
    if (rustdeskId.isNotEmpty && rustdeskId != '0') break;
    await Future<void>.delayed(const Duration(milliseconds: 500));
  }
  if (rustdeskId.isNotEmpty && rustdeskId != '0') {
    final conf = await _httpJson(
      uri: _urlApi(link.apiBase, '/deskremote/dispositivo/id'),
      method: 'POST',
      body: {'rustdesk_id': rustdeskId},
      bearer: deviceToken,
    );
    rustdeskId = (conf['rustdesk_id'] ?? rustdeskId).toString();
  }
  final versao = json['senha_versao'];
  final row = DispositivoDeskRemote(
    apiBase: link.apiBase,
    token: deviceToken,
    senhaVersao: versao is int ? versao : int.tryParse('$versao') ?? 0,
    rustdeskId: rustdeskId.isEmpty ? null : rustdeskId,
  );
  gravarDispositivoDeskRemote(row);
  return row;
}

Future<void> sincronizarSenhaDeskRemote() async {
  final atual = lerDispositivoDeskRemote();
  if (atual == null) return;
  final json = await _httpJson(
    uri: _urlApi(atual.apiBase, '/deskremote/dispositivo/config'),
    method: 'GET',
    bearer: atual.token,
  );
  final senha = (json['senha'] ?? '').toString();
  final servidor = json['servidor'];
  final mapa = servidor is Map ? Map<String, dynamic>.from(servidor) : <String, dynamic>{};
  await aplicarServidorDeskRemote(
    servidorId: (mapa['servidor_id'] ?? '').toString(),
    relay: (mapa['servidor_relay'] ?? '').toString(),
    chave: (mapa['chave'] ?? '').toString(),
  );
  await travarSenhaPermanenteDeskRemote();
  if (senha.isNotEmpty) {
    await _gravarSenhaPermanenteDeskRemote(senha);
  }
  var rustdeskId = (json['rustdesk_id'] ?? atual.rustdeskId)?.toString();
  if (rustdeskId != null && rustdeskId.trim().isEmpty) rustdeskId = null;
  final localId = await idLocalDeskRemote();
  if ((rustdeskId == null || rustdeskId.isEmpty) && localId.isNotEmpty && localId != '0') {
    try {
      final conf = await _httpJson(
        uri: _urlApi(atual.apiBase, '/deskremote/dispositivo/id'),
        method: 'POST',
        body: {'rustdesk_id': localId},
        bearer: atual.token,
      );
      rustdeskId = (conf['rustdesk_id'] ?? localId).toString();
    } on DeskRemoteEnrollErro {
      rustdeskId = localId;
    }
  }
  final versao = json['senha_versao'];
  gravarDispositivoDeskRemote(
    DispositivoDeskRemote(
      apiBase: atual.apiBase,
      token: atual.token,
      senhaVersao: versao is int ? versao : atual.senhaVersao,
      rustdeskId: rustdeskId,
    ),
  );
}
