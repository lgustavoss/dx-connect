import 'dart:async';
import 'dart:convert';
import 'dart:io';

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
  DeskRemoteAuthErro(this.mensagem, {this.status, this.ehRede = false});
  final String mensagem;
  final int? status;
  final bool ehRede;

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
  client.userAgent = 'DeskRemote/2.1.1';
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

/// Rótulo do vínculo na frota (um PDV). Sem sessão, sem permissão ou ID
/// repetido: `null` — a aba cai no alias/`name=` ou em usuário@host.
Future<String?> buscarRotuloVinculoDeskRemote(String rustdeskId) async {
  final alvo = _soDigitosId(rustdeskId);
  if (alvo.isEmpty) return null;
  var sessao = lerSessaoDeskRemote();
  if (sessao == null) return null;

  Future<Map<String, dynamic>> listar(DeskRemoteSessao s) => _httpJson(
        uri: urlApi(s.slug, '/rustdesk/peers').replace(
          queryParameters: const {'filtro': 'vinculado'},
        ),
        method: 'GET',
        bearer: s.accessToken,
      );

  try {
    return await () async {
      Map<String, dynamic> json;
      try {
        json = await listar(sessao);
      } on DeskRemoteAuthErro catch (e) {
        if (e.status != 401) return null;
        final nova = await renovarSessaoDeskRemote(sessao);
        if (nova == null) return null;
        gravarSessaoDeskRemote(nova);
        sessao = nova;
        json = await listar(sessao);
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
