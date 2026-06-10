# kamex

`kamex` は、OpenAI API をモデル推論インターフェースとして利用する、自作 Codex 風の CLI コーディング支援エージェントです。

本システムは、OpenAI APIを利用して独自に実装したコーディング支援エージェントです。
OpenAI Codex、Codex CLI、Agents SDK、Agent Skills、およびMCP（Model Context Protocol）は使用していません。

モデルへの入力、ファイル操作、コマンド実行、差分生成、承認フローは、すべて本システム側で独自に実装・制御しています。
OpenAI APIは、自然言語処理およびコード生成のためのモデル推論機能として利用します。必要な場合のみ、ユーザー承認後にOpenAI Responses APIの `web_search` tool を利用してWeb検索も行います。

## 技術スタック

- Python 3.11+
- OpenAI Python SDK
- Rich
- pytest

このリポジトリは空の新規プロジェクトだったため、実装の簡潔さ、安全なファイル操作、テスト容易性を優先して Python を採用しました。CLI 表示には Rich を使い、エージェント制御、調査、承認、diff生成、shell実行制御はすべて本アプリケーション側で実装しています。

## ディレクトリ構成

```text
.
├── pyproject.toml
├── README.md
├── src/
│   └── kame_agent/
│       ├── agent.py        # 複数ターンのエージェント制御
│       ├── cli.py          # CLI UI
│       ├── commands.py     # shell実行ラッパー
│       ├── config.py       # 環境変数と.env読み込み
│       ├── diffing.py      # unified diff生成
│       ├── fs.py           # 安全なファイル読み書き
│       ├── llm.py          # OpenAI API接続とJSON解析
│       ├── models.py       # 型付きデータモデル
│       ├── prompts.py      # system promptとJSON出力指示
│       ├── safety.py       # path/shell安全ポリシー
│       └── scanner.py      # workspace調査
└── tests/
    ├── test_changes.py
    └── test_safety.py
```

安全境界をテストしやすくするため、ファイル操作、shell制御、diff生成、LLM接続を小さなモジュールに分けています。

## インストール

GitHubからcloneした直後に `kamex` コマンドを登録する場合:

macOS / Linux:

```bash
git clone https://github.com/kamekingdom/kamex.git
cd kamex
python3 scripts/install_kamex.py
kamex --help
```

Windows PowerShell:

```powershell
git clone https://github.com/kamekingdom/kamex.git
cd kamex
python scripts\install_kamex.py
kamex --help
```

ショートカットスクリプトも用意しています。

```bash
./install.sh
```

```powershell
.\install.ps1
```

```cmd
install.bat
```

`scripts/install_kamex.py` は、仮想環境内ではその環境へ、仮想環境外では `python -m pip install --user -e .` 相当でユーザー環境へeditable installします。`kamex` の配置先がPATHに無い場合は、追加すべきディレクトリを表示します。

開発用に仮想環境へ入れる場合:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
kamex --help
```

Windows PowerShell の例:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
kamex --help
```

## 環境変数

推奨:

```bash
export OPENAI_API_KEY="your_api_key"
```

任意:

```bash
export OPENAI_MODEL="gpt-5.3-codex"
```

`OPENAI_API_KEY` が環境変数、workspaceの `.env`、カレントディレクトリの `.env`、ユーザー設定のいずれにも存在しない場合、`kamex` は最初にCLI UI上でAPIキーの入力を求めます。入力はパスワード形式で表示されず、次回以降も使えるようにユーザー設定ファイルへ保存されます。

保存先:

- `KAMEX_CONFIG_DIR` が設定されている場合: `$KAMEX_CONFIG_DIR/.env`
- Windows: `%APPDATA%/kamex/.env`
- macOS/Linux: `$XDG_CONFIG_HOME/kamex/.env` または `~/.config/kamex/.env`

workspaceの `.env` も読み込みます。ただし `.env` や鍵ファイルは LLM 入力対象から除外され、変更対象としても拒否されます。APIキー保存はアプリ専用のユーザー設定に行い、対象workspaceを勝手に変更しません。

使用履歴はユーザー設定ディレクトリの `usage_history.jsonl` に保存されます。タスク完了時には現在タスクと累計のトークン数、概算費用を表示します。価格はモデルごとに変わるため、内蔵価格表にないモデルは費用を `unknown` として記録します。
タスク要約はworkspaceごとの簡易メモリとして `memory/*.jsonl` に、ターンごとの作業記録は `sessions/*.jsonl` に保存されます。保存対象はタスク名、要約、変更ファイル、検証コマンドの終了コードなどで、ファイル全文やコマンド出力全文は保存しません。

価格を上書きする場合:

```bash
export KAMEX_PRICE_GPT_5_3_CODEX_INPUT_PER_1M="1.75"
export KAMEX_PRICE_GPT_5_3_CODEX_OUTPUT_PER_1M="14.0"
```

## 使い方

`--workspace` を指定しない場合、`kamex` はコマンドを実行したカレントディレクトリ、つまり Python の `Path.cwd()` をデフォルトworkspaceとして扱います。`--workspace <path>` を指定した場合のみ、そのパスをworkspaceとして調査・編集します。
対話モードでは、ユーザーがタスクを入力するまでworkspace調査やファイル候補収集を開始しません。空入力は無視されます。

更新確認は自動では行いません。必要なときに `kamex update` を実行するとGitHub Releasesの最新バージョンを確認します。現在のバージョンより新しいものが見つかった場合、CLI上で更新するか確認し、承認されたときだけ `python -m pip install --upgrade git+https://github.com/kamekingdom/kamex.git` を実行します。

ヘルプ:

```bash
kamex --help
```

対話モード:

```bash
kamex
```

対話モードでは、起動時に対象workspaceと現在使用しているOpenAIモデルを表示します。
タスク完了時にはOpenAI APIレスポンスから集計した入力・出力・合計トークン数と概算費用も表示します。

ワンショット実行:

```bash
cd ~/projects/my-app
kamex "READMEを現在の実装に合わせて更新して"
```

この例では `~/projects/my-app` がworkspaceになります。

明示的に読ませたいファイルがある場合は `@path` を使えます。

```bash
kamex " @src/app.py と @tests/test_app.py を見て失敗しているテストを直して"
```

`@path` で指定されたファイルは、通常のreading planより優先して読み取り対象になります。秘密情報ファイル、workspace外パス、巨大ファイル、バイナリファイルは引き続き拒否されます。

workspace指定:

```bash
kamex --workspace ./sample_project "pytestが通るように修正して"
kamex --workspace ./sample_project "このTypeScriptプロジェクトのlintエラーを直して"
```

指定workspaceで対話モード:

```bash
kamex --workspace ./sample_project
```

`--workspace` が指定された場合は、現在のディレクトリではなく指定パスだけをworkspaceとして扱います。

一時的なモデル指定:

```bash
kamex --model gpt-5.3-codex "READMEを改善して"
```

バージョン表示:

```bash
kamex version
kamex --version
```

更新確認:

```bash
kamex update
```

workspaceごとの直近履歴:

```bash
kamex history
```

直近タスクを現在のworkspace状態から再開:

```bash
kamex resume
```

`kamex resume` は直近のタスク名、簡易メモリ、セッションログ要約、現在のファイル状態を使って再開用プロンプトを作り、通常のagent loopを実行します。

環境変数でも制御できます。

```bash
export KAMEX_DISABLE_UPDATE_CHECK=1
export KAMEX_UPDATE_URL="https://api.github.com/repos/kamekingdom/kamex/releases/latest"
export KAMEX_UPDATE_INSTALL_SPEC="git+https://github.com/kamekingdom/kamex.git"
```

Web検索を無効化:

```bash
kamex --no-web-search
```

モデルが「現在のライブラリ仕様」「最新ドキュメント」「未知のエラー」など外部情報が必要だと判断した場合、kamexは検索クエリをCLIに表示します。ユーザーが承認した場合のみ、OpenAI APIのWeb検索を実行し、その結果を変更案生成に渡します。

1タスクあたりの最大ターン数を変更:

```bash
kamex --max-turns 8 "テストが通るまで修正して"
```

kamexは、変更後に検証コマンドが失敗した場合や、変更後に検証出力がない場合、更新後のworkspaceと前ターンの観測結果をもとに次のターンへ進みます。最大ターン数に達した場合は安全側に停止して対話プロンプトへ戻ります。

workspaceスキャン時には、ファイル名だけでなくタスク語句に一致する本文行も軽く検索し、関連スニペットをOpenAI APIへの文脈に含めます。これにより、ファイル名に手掛かりがない実装でもreading planに入りやすくなります。

初回読み取り後に、足りない関連ファイルを追加で探す回数を変更:

```bash
kamex --max-context-rounds 3 "認証まわりの不具合を直して"
```

追加探索を止めたい場合は `--max-context-rounds 0` を指定します。

allowlist内の検証コマンドは自動実行されます。従来のように毎回確認したい場合:

```bash
kamex --no-auto-run-safe-commands "テストが通るまで修正して"
```

変更案は表示前に追加のモデルレビューを通します。API呼び出し回数を減らしたい場合:

```bash
kamex --no-review "小さな修正をして"
```

プロジェクト指示ファイル:

```bash
AGENTS.md
CLAUDE.md
KAMEX.md
```

kamexはworkspace配下の `AGENTS.md`、`CLAUDE.md`、`KAMEX.md` を読み込み、OpenAI APIへ渡すプロジェクト文脈に含めます。これらのファイルには、コーディング規約、検証コマンド、避けるべき変更、よく使うワークフローを書けます。

## 動作フロー

1. ユーザー指示を受け取る
2. APIキーが未設定ならCLI UI上で入力を受け取り保存する
3. 現在のworkspace配下のサブディレクトリを含めて候補ファイルを調査し、タスク語句で本文スニペットを検索する
4. `AGENTS.md`、`CLAUDE.md`、`KAMEX.md` などのプロジェクト指示を読み込む
5. ユーザー指示内の `@path` 明示ファイルを抽出する
6. 言語、パッケージマネージャ、テスト候補を推定する
7. OpenAI APIに読むべきファイルと必要なWeb検索クエリの計画をJSONで生成させる
8. 安全ポリシーを通過したファイルだけを読む
9. 読み取り済みコンテキストを見直し、必要なら関連ファイルを追加で読む
10. Web検索が必要な場合、検索クエリを表示してユーザー承認後にOpenAI APIで検索する
11. OpenAI APIに構造化された変更案JSONを生成させる
12. 変更案を追加のモデルレビューへ通し、安全性、読み落とし、検証不足を確認・修正する
13. アプリ側で変更案を検証してdiffを生成する
14. CLIにdiffを表示する
15. ユーザー承認後にのみファイルへ適用する
16. 提案されたコマンドを表示し、安全ポリシー確認後、allowlist内の検証コマンドは自動実行し、それ以外はユーザー承認後にのみ実行する
17. コマンド失敗や未検証の変更があれば、観測結果を次ターンへ渡して再調査・再提案する
18. タスクが完了したと判断したら、結果、簡易メモリ、セッションログ、使用トークン数、概算費用、累計使用履歴を要約する

## 安全設計

- workspace外のパスを拒否
- ユーザー指示が入力されるまでworkspace調査を開始しない
- LLMへ渡す候補ファイル一覧は現在のworkspace配下から収集し、設定ファイルとユーザー指示に関係するファイルを優先表示する
- タスク語句に一致した本文スニペットをLLM文脈に含め、本文から関連ファイルを見つけやすくする
- `AGENTS.md`、`CLAUDE.md`、`KAMEX.md` はプロジェクト指示として読み込み、秘密情報ファイルや巨大ファイルは除外する
- `--workspace` 未指定時のworkspaceはコマンド実行時のカレントディレクトリ
- `--workspace` 指定時のみ指定パスをworkspaceとして使用
- 絶対パスを拒否
- `../` を含むパスを拒否
- シンボリックリンク経由のworkspace外アクセスを拒否
- 巨大ファイルとバイナリファイルを読み込み対象から除外
- `.env`, `.env.local`, `id_rsa`, `id_ed25519`, `*.pem`, `*.key`, `credentials.json` を秘密情報として除外
- LLMの変更案は `create` / `modify` と変更後全文のJSONだけを受け付ける
- Web検索クエリはCLI上に表示し、ユーザー承認後にのみOpenAI APIで実行
- `--no-web-search` でWeb検索を完全に無効化可能
- OpenAI APIレスポンスのusage情報を集計し、タスク完了時にトークン数として表示
- 使用履歴をユーザー設定ディレクトリのJSONLへ追記
- 簡易メモリとセッションログはユーザー設定ディレクトリへworkspace別に保存
- `kamex resume` は保存済みログと現在のworkspaceを使って直近タスクを再開
- モデル別価格表または環境変数から概算費用を計算
- `modify` は既存ファイルのみ許可
- `create` は未存在ファイルのみ許可
- diff表示とユーザー承認前には書き込みを行わない
- shellは `shell=False` で実行
- shellコマンドの実行cwdをworkspaceに固定
- コマンドの標準入力は閉じて実行し、入力待ちでCLIが止まらないようにする
- コマンドが120秒を超えた場合はタイムアウト結果として表示し、対話モードへ戻る
- shell制御演算子を拒否
- 検査系コマンドはallowlistで自動実行
- `--no-auto-run-safe-commands` で検査系コマンドも承認制に戻せる
- `--no-review` で追加のモデルレビューを無効化できる
- allowlist外のコマンドは、一回限りのユーザー承認を求めてから実行
- `rm` や `pip install` などの高リスクコマンドは、high-risk one-time approval として強調表示してから実行確認
- LLMがshell制御演算子を含む不正なコマンドを提案した場合、ファイル変更案は継続し、そのコマンドだけをスキップしてNotesに表示

高リスク承認として表示されるコマンド例:

```text
rm, sudo, chmod, chown, curl, wget, ssh, scp, rsync, git push,
git reset --hard, docker, kill, pkill, shutdown, reboot,
npm publish, pip install
```

許可される検査系コマンド例:

```text
git status
git diff
pytest
python -m pytest
python -m unittest
mypy
pyright
ruff check
npm test
npm run lint
npm run typecheck
npm run build
pnpm run check
yarn run build
cargo test
cargo check
go test
go vet
make test
make check
```

allowlist外でも、高リスク分類ではなくshell制御演算子を含まないものは、CLI上で「one-time user approval」として表示されます。ユーザーが明示的に承認した場合のみ、その1回だけworkspaceをcwdとして実行します。

`rm` や `pip install` のような高リスクコマンドも、CLI上で「high-risk one-time approval」として表示されます。ユーザーが明示的に承認した場合のみ、その1回だけworkspaceをcwdとして実行します。`&&`, `|`, `>`, `<` などのshell制御演算子は引き続き拒否します。

## テスト

```bash
python -m pytest
```

検証している内容:

- workspace外ファイルにアクセスできない
- `../` を含む危険パスが拒否される
- symlink経由のworkspace外アクセスが拒否される
- 秘密情報ファイルをLLM入力対象にしない
- shell制御演算子を含むコマンドが拒否される
- 検査系コマンドと、一回限りで承認されたコマンドのみ実行できる
- 入力待ちや長時間実行になったコマンドでもCLIがクラッシュせず、観測結果として次ターンへ渡せる
- Web検索が必要な場合だけ、ユーザー承認後にOpenAI APIで検索できる
- 空入力ではタスク実行やworkspace調査を開始しない
- プロンプトに応じて候補ファイル一覧の優先順位が変わる
- 使用トークン数がタスク完了時に表示される
- 概算費用と累計使用履歴が保存・表示される
- 変更案からdiffを生成できる
- ユーザー承認前にファイルが変更されない
- 承認後にのみ変更が適用される
- `create` / `modify` の挙動が正しい

## 現在の制限

- 1タスクの継続ターン数は `--max-turns` の上限で停止します。
- 追加ファイル探索は `--max-context-rounds` の上限で停止します。
- `kamex resume` はログから再開用プロンプトを作る補助機能で、完全な端末状態やLLM内部状態の復元ではありません。
- 追加のモデルレビューは品質向上を狙うため、通常よりAPI呼び出し回数が増えます。
- ファイル適用、allowlist外コマンド、高リスクコマンドは各ターンでユーザー承認が必要です。
- LLM出力はJSONとして解析しますが、モデルが不正なJSONを返した場合は安全側に倒して停止します。
- ファイル全体更新方式のため、巨大ファイルの編集は拒否します。
- shell制御演算子を含むコマンドはユーザー承認があっても拒否します。

## 今後の拡張予定

- 変更対象が大きい場合の分割編集形式
- プロジェクトごとの安全ポリシー設定
- dry-run専用モード
- JSON Schemaによるさらに厳密なLLM出力制約
- 実行履歴の保存と監査ログ
