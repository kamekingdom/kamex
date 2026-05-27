# kamex

`kamex` は、OpenAI API をモデル推論インターフェースとして利用する、自作 Codex 風の CLI コーディング支援エージェントです。

本システムは、OpenAI APIを利用して独自に実装したコーディング支援エージェントです。
OpenAI Codex、Codex CLI、Agents SDK、Agent Skills、およびMCP（Model Context Protocol）は使用していません。

モデルへの入力、ツール呼び出し、ファイル操作、コマンド実行、差分生成、承認フローは、すべて本システム側で独自に実装・制御しています。
OpenAI APIは、自然言語処理およびコード生成のためのモデル推論機能としてのみ利用しています。

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

## 使い方

`--workspace` を指定しない場合、`kamex` はコマンドを実行したカレントディレクトリ、つまり Python の `Path.cwd()` をデフォルトworkspaceとして扱います。`--workspace <path>` を指定した場合のみ、そのパスをworkspaceとして調査・編集します。

ヘルプ:

```bash
kamex --help
```

対話モード:

```bash
kamex
```

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

## 動作フロー

1. ユーザー指示を受け取る
2. APIキーが未設定ならCLI UI上で入力を受け取り保存する
3. workspaceを調査する
4. 言語、パッケージマネージャ、テスト候補を推定する
5. OpenAI APIに読むべきファイルの計画をJSONで生成させる
6. 安全ポリシーを通過したファイルだけを読む
7. OpenAI APIに構造化された変更案JSONを生成させる
8. アプリ側で変更案を検証してdiffを生成する
9. CLIにdiffを表示する
10. ユーザー承認後にのみファイルへ適用する
11. 提案されたコマンドを表示し、安全ポリシー確認後、ユーザー承認後にのみ実行する
12. 結果を要約する

## 安全設計

- workspace外のパスを拒否
- `--workspace` 未指定時のworkspaceはコマンド実行時のカレントディレクトリ
- `--workspace` 指定時のみ指定パスをworkspaceとして使用
- 絶対パスを拒否
- `../` を含むパスを拒否
- シンボリックリンク経由のworkspace外アクセスを拒否
- 巨大ファイルとバイナリファイルを読み込み対象から除外
- `.env`, `.env.local`, `id_rsa`, `id_ed25519`, `*.pem`, `*.key`, `credentials.json` を秘密情報として除外
- LLMの変更案は `create` / `modify` と変更後全文のJSONだけを受け付ける
- `modify` は既存ファイルのみ許可
- `create` は未存在ファイルのみ許可
- diff表示とユーザー承認前には書き込みを行わない
- shellは `shell=False` で実行
- shellコマンドの実行cwdをworkspaceに固定
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
