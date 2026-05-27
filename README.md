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
│       ├── agent.py        # 1タスク1サイクルのエージェント制御
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
export OPENAI_MODEL="gpt-5.2"
```

`OPENAI_API_KEY` が環境変数、workspaceの `.env`、カレントディレクトリの `.env`、ユーザー設定のいずれにも存在しない場合、`kamex` は最初にCLI UI上でAPIキーの入力を求めます。入力はパスワード形式で表示されず、次回以降も使えるようにユーザー設定ファイルへ保存されます。

保存先:

- `KAMEX_CONFIG_DIR` が設定されている場合: `$KAMEX_CONFIG_DIR/.env`
- Windows: `%APPDATA%/kamex/.env`
- macOS/Linux: `$XDG_CONFIG_HOME/kamex/.env` または `~/.config/kamex/.env`

workspaceの `.env` も読み込みます。ただし `.env` や鍵ファイルは LLM 入力対象から除外され、変更対象としても拒否されます。APIキー保存はアプリ専用のユーザー設定に行い、対象workspaceを勝手に変更しません。

使用履歴はユーザー設定ディレクトリの `usage_history.jsonl` に保存されます。タスク完了時には現在タスクと累計のトークン数、概算費用を表示します。価格はモデルごとに変わるため、内蔵価格表にないモデルは費用を `unknown` として記録します。

価格を上書きする場合:

```bash
export KAMEX_PRICE_GPT_5_2_INPUT_PER_1M="1.25"
export KAMEX_PRICE_GPT_5_2_OUTPUT_PER_1M="10.0"
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
kamex --model gpt-5.2 "READMEを改善して"
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

## 動作フロー

1. ユーザー指示を受け取る
2. APIキーが未設定ならCLI UI上で入力を受け取り保存する
3. ユーザー指示に関係する候補ファイルと設定ファイルに絞ってworkspaceを調査する
4. 言語、パッケージマネージャ、テスト候補を推定する
5. OpenAI APIに読むべきファイルと必要なWeb検索クエリの計画をJSONで生成させる
6. 安全ポリシーを通過したファイルだけを読む
7. Web検索が必要な場合、検索クエリを表示してユーザー承認後にOpenAI APIで検索する
8. OpenAI APIに構造化された変更案JSONを生成させる
9. アプリ側で変更案を検証してdiffを生成する
10. CLIにdiffを表示する
11. ユーザー承認後にのみファイルへ適用する
12. 提案されたコマンドを表示し、安全ポリシー確認後、ユーザー承認後にのみ実行する
13. 結果、使用トークン数、概算費用、累計使用履歴を要約する

## 安全設計

- workspace外のパスを拒否
- ユーザー指示が入力されるまでworkspace調査を開始しない
- LLMへ渡す候補ファイル一覧はユーザー指示に関係するものと設定ファイルに限定
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
- モデル別価格表または環境変数から概算費用を計算
- `modify` は既存ファイルのみ許可
- `create` は未存在ファイルのみ許可
- diff表示とユーザー承認前には書き込みを行わない
- shellは `shell=False` で実行
- shellコマンドの実行cwdをworkspaceに固定
- コマンドの標準入力は閉じて実行し、入力待ちでCLIが止まらないようにする
- コマンドが120秒を超えた場合はタイムアウト結果として表示し、対話モードへ戻る
- shell制御演算子を拒否
- 検査系コマンドはallowlistで通常の承認対象として表示
- allowlist外のコマンドは、一回限りのユーザー承認を求めてから実行
- `rm` や `pip install` などの高リスクコマンドは、high-risk one-time approval として強調表示してから実行確認
- LLMがshell制御演算子を含む不正なコマンドを提案した場合、ファイル変更案は継続し、そのコマンドだけをスキップしてNotesに表示
- `git status` と `git diff` のみ自動実行

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
mypy
ruff check
npm test
npm run lint
npm run typecheck
cargo test
go test
make test
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
- 入力待ちや長時間実行になったコマンドでもCLIがクラッシュせず対話モードへ戻る
- Web検索が必要な場合だけ、ユーザー承認後にOpenAI APIで検索できる
- 空入力ではタスク実行やworkspace調査を開始しない
- プロンプトに応じて候補ファイル一覧が絞られる
- 使用トークン数がタスク完了時に表示される
- 概算費用と累計使用履歴が保存・表示される
- 変更案からdiffを生成できる
- ユーザー承認前にファイルが変更されない
- 承認後にのみ変更が適用される
- `create` / `modify` の挙動が正しい

## 現在の制限

- 初期版は1タスク1サイクルです。
- テスト失敗後の自動再計画と再修正は未実装です。
- LLM出力はJSONとして解析しますが、モデルが不正なJSONを返した場合は安全側に倒して停止します。
- ファイル全体更新方式のため、巨大ファイルの編集は拒否します。
- shell制御演算子を含むコマンドはユーザー承認があっても拒否します。

## 今後の拡張予定

- テスト失敗ログをもとにした再計画ループ
- 変更対象が大きい場合の分割編集形式
- プロジェクトごとの安全ポリシー設定
- dry-run専用モード
- JSON Schemaによるさらに厳密なLLM出力制約
- 実行履歴の保存と監査ログ
