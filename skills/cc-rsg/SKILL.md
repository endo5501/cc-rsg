---
name: cc-rsg
description: 既存のコードベースから仕様書を逆生成(リバースエンジニアリング)するための汎用フレームワーク。ゴール駆動の偵察、WBS分割による並列調査、Question Bankを介した対話的精緻化により、メンテナンス担当者または納品先顧客に向けた信頼性の高い仕様書一式を生成する。Reverse-engineer comprehensive specification documents from existing codebases through goal-driven reconnaissance, WBS-based parallel investigation, and iterative question-bank dialogue.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task, AskUserQuestion, WebFetch, WebSearch
---

# cc-rsg (Claude Code Reverse Spec Generator)

既存のコードベース(レガシーまたは現役を問わず)から、メンテナンス担当者あるいは納品先顧客に向けた仕様書を逆生成する汎用フレームワーク。

このスキルは「コード→仕様」のreverse方向であり、`cc-sdd`(Spec Driven Development、仕様駆動開発)の対概念として位置づけられる。両者は同一系譜の対称的なツールである。

---

## 設計原則

このスキルは以下11の原則に基づいて動作する。原則同士は相互補完的であり、いずれかが破綻するとスキル全体の信頼性が失われる。

1. **ゴール駆動**: Phase 0で5問の選択型対話によりゴールを確定し、`.cc-rsg/goal.json`に永続化。全フェーズで参照される。
2. **テンプレートのハイブリッド決定**: 利用者が用意したテンプレート、Claudeが偵察結果から推奨するテンプレート、推奨を利用者が手直ししたものの三方向に対応する。
3. **インベントリ単位の参照ベース選択**: `references/inventory-units.md`に言語・フレームワーク別の典型単位を列挙し、対象コードベースに該当するパターンを選択する。
4. **抜け漏れ防止はインベントリベース検証を主軸とする**: コードから抽出可能な単位を全件列挙し、仕様書がそれらをカバーしているかを機械的に検査する。
5. **Question Bankは3タイミングで生成する**: 偵察末尾(大局的疑問)、サブエージェント実行中(詳細疑問)、検証時(整合性疑問)。7標準カテゴリで分類する。
6. **サブエージェントは疑問の深刻度で動的判断する**: criticalなら章を保留、important / nice-to-haveなら推測で進めつつマーカーを残す。
7. **疑問の統合は「明らかに同一」のみ自動マージする**: 「似ているが微妙に違う」はグループ化してユーザーに判断を求める。
8. **対話プロトコルはClaudeが自動駆動する**: 選択肢提示を基本とし、自由入力は余白として用意。AskUserQuestion等の選択型UIを最大限活用する。
9. **回答不能な疑問は`abandoned`としてマークする**: 最終仕様書に「未確定事項」として明示的に記載する。隠さない。
10. **二重消費者対応はゴール定義で1つに絞る**: 複数ビューが必要なら再起動で対応する。
11. **出力言語はPhase 0で選択する (English / 日本語)**: 最初の対話のみバイリンガルで出力言語を尋ね、`.cc-rsg/goal.json` の `output_language` に永続化(`"en"` または `"ja"`)。以降のすべてのユーザー対話(AskUserQuestion質問文・選択肢、進捗メッセージ、確認サマリ)、生成される仕様書本文・章タイトル、`questions.json` の `body` / `answer`、Phase 4検証レポート、再開メッセージ等の自然言語出力は当該言語に統一する。一方、内部識別子と機械可読要素 — 状態キー(`current_phase` 等)、ID(`Q-XXX` / `INV-XXX`)、ファイル名(ASCII slug)、`[REF: file:lines]`、`[CONFIDENCE: HIGH|MED|LOW]`、`[ASK SME]`、`[ASSUMED: ...]`、`[BLOCKED: ...]` 等のマーカー名、`goal.json` の列挙値(`primary_reader: "maintenance_developer"` 等) — は言語非依存のまま英語固定で維持する。スキル本体のSKILL.md・`references/*.md`・`templates/*.md` は日本語で記述されておりClaudeが内部参照する設計だが、`output_language == "en"` の場合は出力時に意味的に等価な英語に動的翻訳する(テンプレートの章見出し例、参照ガイドの例文を含む)。

---

## 6フェーズ状態マシンの全体像

スキル全体は以下6フェーズの状態マシンとして実装される。各フェーズは`.cc-rsg/state.json`で進捗管理され、中断・再開可能。

| Phase | 名称 | 主たる成果物 |
|-------|------|------------|
| 0 | Setup & Goal | `.cc-rsg/goal.json` |
| 1 | Recon & Template | `recon-report.md`, テンプレート選定結果 |
| 2 | Plan & WBS | `inventory.json`, `wbs.json` |
| 3 | Investigate | `drafts/*.md`(各章ドラフト) |
| 4 | Verify | カバレッジレポート、整合性疑問 |
| 5 | Refine via Dialogue | 解消された`questions.json` |
| 6 | Deliver | `final/`配下の最終仕様書一式 |

各フェーズの詳細は次節以降で定義する。

---

## Phase 0: Setup & Goal(セットアップとゴール定義)

### 目的
スキル起動直後に、対象範囲とゴールを確定する。これ以降のすべての判断はここで定義したゴールに従属する。

### 動作手順

1. **プロジェクト確認**
   - 現在のワーキングディレクトリを起点として、対象プロジェクトの所在を確認する。
   - 利用者に「対象とするコードベースのルートディレクトリはここで合っていますか?」と問う。違う場合は正しいパスを取得する。

2. **状態ディレクトリの初期化**
   - `.cc-rsg/`ディレクトリを作成。
   - 既存の`.cc-rsg/state.json`がある場合は再開モードへ分岐(後述「状態管理と再開」を参照)。

3. **出力言語の選択 (Output language selection)**
   - **この手順のみバイリンガルで提示する**。ユーザーの希望言語が未確定なため、質問文と選択肢ラベルを英語と日本語の両方で表記する。
   - AskUserQuestionで以下を提示する:
     - 質問文: `Select output language for dialogue and generated specs / 対話と生成ドキュメントの出力言語を選択してください`
     - 選択肢（**順序固定: 日本語が先頭・デフォルト**）:
       - `日本語 (Japanese)`
       - `English`
   - 選択結果を `output_language` として記憶する(`日本語` → `"ja"` / `English` → `"en"`)。永続化は手順5で他項目とまとめて行う。
   - **デフォルト方針**: ユーザーが選択肢に手を加えなかった場合は `"ja"` を選んだものとして扱う(日本語環境を主要想定とするため)。英語利用時は明示的に `English` を選ばせる。
   - **以降の手順4以降のすべての自然言語出力(AskUserQuestion質問文・選択肢、確認サマリ、章タイトル、生成ドキュメント、`questions.json` の本文等)は、ここで選択された言語で行う**(設計原則11参照)。
   - 既存 `.cc-rsg/goal.json` が存在する再開時は、保存済みの `output_language` を読み込み本手順をスキップする。

4. **ゴール定義5問の実施**
   - AskUserQuestionツールで以下5問を順次質問する。**質問文・選択肢ラベル・自由入力欄のプレースホルダはすべて手順3で選択した `output_language` で表示する**。以下は日本語版の文面。`output_language == "en"` の場合は意味的に等価な英訳を動的に生成する(列挙値そのもの — `primary_reader: "maintenance_developer"` 等 — は言語非依存の英語enumとして `goal.json` に保存)。各問は選択型を基本とし、自由入力欄を補助として設ける。

   **Q1. 仕様書の主たる読者は誰ですか?**
   - メンテナンス開発者
   - 納品先顧客
   - SME(業務有識者)
   - 規制当局
   - その他(自由入力)

   **Q2. 仕様書を読んだ後、その読者は何をしますか?**
   - コード変更
   - 承認判断
   - 監査
   - 学習
   - その他(自由入力)

   **Q3. 仕様書の粒度希望はどの程度ですか?**
   - 高レベル概要
   - 中粒度
   - 詳細
   - その他(自由入力)

   **Q4. 重視する観点を選んでください(複数選択可)**
   - 機能正確性
   - 業務妥当性
   - セキュリティ
   - 運用性
   - 性能
   - その他(自由入力)

   **Q5. 既存資料の有無と扱いは?**
   - 既存資料なし
   - 既存資料あり / 更新したい
   - 既存資料あり / 併存させたい
   - 既存資料あり / 廃止したい
   - その他(自由入力)

5. **`goal.json`への永続化**
   - 手順3の言語選択と手順4の5問の回答を構造化して`.cc-rsg/goal.json`に保存する。スキーマは以下。

   ```json
   {
     "output_language": "ja",
     "primary_reader": "maintenance_developer",
     "reader_action": "code_change",
     "granularity": "medium",
     "perspectives": ["functional_correctness", "operational"],
     "existing_docs": "none",
     "free_text_notes": "..."
   }
   ```
   - `output_language` は `"en"` または `"ja"` のいずれか必須。他の列挙値(`primary_reader`, `reader_action`, `granularity`, `perspectives`, `existing_docs`)は言語非依存の英語enum値で固定する(表示時に `output_language` でローカライズして提示する)。

6. **Phase 0完了**
   - `state.json`を更新し、Phase 1へ進む。

### このフェーズで気を付けること
- 利用者の負担を最小化するため、選択型UIを優先し、毎回タイピングを強要しない。
- 自由入力欄は「上記に当てはまらない場合」の保険として用意し、選択肢を選んだ場合は不要。
- ゴールは後続全フェーズに影響するため、回答内容を要約して利用者に再確認する一手間を惜しまない。**確認サマリも `output_language` で出力する**。
- 出力言語選択(手順3)は**最初の対話のみバイリンガル提示**。手順4以降は確定言語のみで進める。ユーザーが途中で言語変更を希望した場合は `goal.json.output_language` を更新し、既存の `drafts/` や `questions.json` 本文の翻訳要否を都度確認する。

---

## Phase 1: Recon & Template(偵察とテンプレート選定)

### 目的
浅い偵察によりコードベースの全体像を把握し、適切な仕様書テンプレートを選定する。Phase 1末尾で大局的な疑問をQuestion Bankに登録する。

### 動作手順

1. **浅い偵察の実施**
   以下を読み取り、`recon-report.md`としてまとめる。
   - ファイルツリーの構造(深さ3〜4程度に制限、ノイズ除外)
   - パッケージマネージャ設定(`package.json`, `composer.json`, `requirements.txt`, `pom.xml`, `build.gradle`等)
   - エントリーポイント候補(main関数、index、ルーティング定義等)
   - 既存ドキュメント(`README.md`, `docs/`, `wiki`等)
   - ビルド・デプロイ設定(`Dockerfile`, `Makefile`, CI設定等)
   - 言語構成と推定行数

2. **テンプレート候補の提示**
   - `references/template-catalog.md`を参照し、対象コードベースに適合する候補を選定する。
   - 利用者にAskUserQuestionで提示する。

   **テンプレート選択肢の例**:
   - 自分で用意したテンプレートがある(パスを指定)
   - Webアプリケーション仕様書(`templates/web-app.md`)
   - バッチ処理システム仕様書(`templates/batch-system.md`)
   - APIサービス仕様書(`templates/api-service.md`)
   - ライブラリ/SDK仕様書(`templates/library-sdk.md`)
   - Claudeが偵察結果から推奨したものを採用

3. **テンプレート確定後の手直し**
   - 利用者がClaude推奨を採用した場合、章立てを表示し「追加・削除・修正したい章はありますか?」と問う。
   - 追加・削除があれば反映する。

4. **大局的疑問の登録**
   - 偵察で生じた根本的な疑問(全体像の把握をブロックする疑問)を`questions.json`に登録する。
   - 例:
     - このシステムが解決しようとしている業務問題は何か
     - 対象範囲はどこまでか(モノリポ内のどのモジュールか)
     - 既存ドキュメントとコードに乖離がある場合どちらを正とするか
   - 登録時の構造は「Question Bank の運用」節を参照。

5. **Phase 1完了**
   - `state.json`を更新し、Phase 2へ進む。

### このフェーズで気を付けること
- 偵察は「浅く広く」が原則。詳細なロジック理解はPhase 3に委ねる。
- ノイズ(node_modules, vendor, .git等)を除外しないと出力が爆発する。
- 利用者がテンプレートを持参した場合は「Claudeが推奨と異なる」ことを指摘してもよいが、決定権は利用者にある。

---

## Phase 2: Plan & WBS(計画とWBS分割)

### 目的
仕様書のスケルトンを確定し、各章を埋めるためのサブタスクをWBSとして分割する。同時にインベントリを抽出して`inventory.json`を生成する。

### 動作手順

1. **章ファイル命名規約の適用とスケルトン生成**
   - すべての章ファイルは以下の命名規約に従う。Claudeが自由に命名することを禁止する。
     - **ファイル名**: `{NN}-{slug}.md`
       - `NN`: 2桁ゼロ埋めの章番号(`00`〜`99`)
       - `slug`: ASCII小文字 + 数字 + ハイフンのみ(例: `01-overview.md`, `04-oauth-oidc.md`)
       - 厳密な正規表現: `^(0\d|[1-9]\d)-[a-z0-9-]+\.md$`
     - **本文章タイトル**: ファイル名と独立に扱う。`goal.json.output_language` に従って出力する(日本語例: `# 第1章: 概要` / 英語例: `# Chapter 1: Overview`)
     - **章番号は Phase 2 でメインエージェントが採番**し、`wbs.json.chapters[].file_name` に確定させる。サブエージェントは命名判断を行わず、メインから渡されたファイル名で必ず保存する。
   - **予約番号 / 予約ファイル名**(必ず生成すること):
     - `00-metadata.md`(メタデータ章)
     - `99-unresolved.md`(未確定事項章)
     - `traceability.md`(トレーサビリティ表、番号なし)
   - 本文章番号は `01`〜`98` の範囲で予約と衝突しないよう連番を振る。
   - **生成タイミング**: Phase 2 の時点で「メタデータ章」「未確定事項章」「トレーサビリティ表」も含む全章ファイルを `drafts/` 配下に空ファイルとして作成する(本文充填は Phase 3 / Phase 6)。
   - 各章ファイル冒頭に「この章で扱う内容」のメタコメント(`<!-- meta: ... -->`)を置く。
   - `00-metadata.md` のスケルトンには「この章は Phase 6 で goal.json / 生成日時 / コミットハッシュ / テンプレート選定結果を記載する」旨をメタコメントで残す。
   - `99-unresolved.md` のスケルトンには「この章は Phase 6 で `questions.json` の `abandoned` エントリを集約する」旨をメタコメントで残す。
   - `traceability.md` のスケルトンには「この章は Phase 6 で章/節とソースコード参照の対応表を出力する」旨をメタコメントで残す。

2. **WBSの作成**
   - 各章を埋めるためのサブタスクを定義する。1サブタスク=1サブエージェントの想定。
   - サブタスクの粒度: 1サブタスクが扱う範囲は「精度を確保できる粒度」に分割する。大きすぎると粗くなり、小さすぎるとオーバーヘッドが増える。
   - WBSは`wbs.json`に保存。スキーマは以下。

   ```json
   {
     "chapters": [
       {
         "chapter_id": "ch-01-overview",
         "chapter_title": "第1章: 概要",
         "file_name": "01-overview.md",
         "assigned_inventory_ids": ["INV-001", "INV-002"],
         "status": "pending"
       }
     ]
   }
   ```

   - `file_name` は必須フィールドで、上記命名規約(`^(0\d|[1-9]\d)-[a-z0-9-]+\.md$`)に合致しなければならない。
   - `00-metadata.md` `99-unresolved.md` `traceability.md` の3ファイルは `wbs.json` の `chapters` 配列に含めるが、`assigned_inventory_ids` は空配列とし、Phase 6 で本文を生成する。

3. **インベントリ抽出（source-map.py 起点）**

   **STEP A（必須）**: `scripts/source-map.py` を実行してソースユニットを自動抽出する:
   ```bash
   python .cc-rsg/skill/scripts/source-map.py \
     --target <対象ルート> \
     --output .cc-rsg/source-map.json
   ```
   これで言語別にクラス・モジュール・ルート・migration・view 等が `SRC-NNNN` として列挙される。

   **STEP B（必須）**: `source-map.json` の `stats.files_scanned` から最低 INV 件数を算出:
   ```
   inventory.json 最低件数 = max(50, files_scanned // 20)
   ```
   この件数を下回ると `coverage-check.py` で fail する。

   **STEP C**: `references/inventory-units.md` を参照し、対象言語のカタログに沿って `source-map.json` のユニットを概念単位にグループ化:
   - 例(言語別):
     - PHP: クラス、トレイト、関数、ルート定義
     - COBOL: PROGRAM-ID、SECTION、PARAGRAPH
     - Python: モジュール、クラス、関数、エンドポイント
     - Java: クラス、メソッド、エンドポイント、エンティティ
     - JavaScript/TypeScript: エクスポート関数、コンポーネント、ルート
     - **Ruby on Rails**: 必ず `inventory-units.md` の「Ruby on Rails 用カタログ」14項目（Controller/Model/Concern/Service/Job/Mailer/Helper/Lib/Migration/Route group/View group/JS module/Config/Mailer template）に沿って網羅する

   **STEP D**: macro/group/module 系の type は禁止。1 class / 1 module / 1 action 単位で記述。

   抽出結果は `inventory.json` に保存。スキーマは以下。

   ```json
   {
     "units": [
       {
         "id": "INV-001",
         "type": "controller",
         "name": "IssuesController",
         "file": "redmine-master/app/controllers/issues_controller.rb",
         "line": 20,
         "covered_by": [],
         "related_source_ids": ["SRC-0142", "SRC-0143"]
       }
     ]
   }
   ```

   `related_source_ids` で source-map.json のユニットと紐付けることで Phase 4 で MECE 検査が可能になる。

4. **WBSと章の対応付け**
   - インベントリの各項目を、どの章で扱うかをWBS上で対応付ける。

5. **利用者レビュー**
   - WBSとスケルトンを表示し、利用者に「この分割でPhase 3を開始してよいか」を確認する。

6. **Phase 2完了**
   - `state.json`を更新し、Phase 3へ進む。

### このフェーズで気を付けること
- インベントリ抽出スクリプトはClaudeがその場で生成する。事前定義された汎用スクリプトでは言語固有の細部に対応できない。
- WBSの粒度設計はサブエージェント精度に直結する。迷ったら細かく分ける。
- 利用者レビューを省略するとPhase 3で大量の手戻りが発生する。
- **章ファイル命名規約は厳密に守ること**。`chapter2_architecture.md` や `第3章_認証.md` のような自由命名は不可。逸脱は `scripts/coverage-check.py` の検証で警告される。

---

## Phase 3: Investigate(調査と章執筆)

### 目的
WBS に基づき、章ごとに **実コードを読んでから本文を書く**。

### 必須原則（厳守）

「コードを開かずに章を書く」を構造的に不可能にするため、各章を以下の順で進める:

#### STEP A: Sources Read（必須・サボると Phase 4 で fail）

その章の `wbs.json.chapters[*].assigned_inventory_ids` に含まれる全 INV について、
対応する **実ソースファイルを `file_editor view` で読む**。

view したファイルパスと行範囲を **章冒頭の `## Sources Read` セクション** に列挙する:

```markdown
# Chapter 5: Data Model

## Sources Read
- `redmine-master/app/models/issue.rb` (lines 1-440)
- `redmine-master/app/models/project.rb` (lines 1-690)
- `redmine-master/app/models/user.rb` (lines 1-120)
- `redmine-master/db/migrate/0042_create_issues.rb` (lines 1-50)
- `redmine-master/app/models/concerns/issue_relations.rb` (lines 1-95)

## 5.1 概要
...
```

**最低 5 ファイル**を Sources Read に列挙すること。`coverage-check.py` がこの数を検査する。
列挙されていないファイル / view 履歴の無いファイルから引用 (`[REF:]`) を書くのは禁止。

#### STEP B: 引用抽出（必須）

view したコードから具体引用を **最低 10 ヶ所** 抽出する:

```
[REF: redmine-master/app/models/issue.rb:42-56]
[REF: redmine-master/app/models/issue.rb:120-145]
...
```

クラス定義、主要メソッド、設定値、コールバック、validation、例外処理 等を網羅。
行範囲は精密に記述する（粗い `:1-500` のような書き方は不可）。

#### STEP C: 章本文の執筆（必須要件）

引用を本文に組み込んで章を執筆。**全章共通の必須要件**:

| 項目 | 最低基準 | 検査スクリプト |
|------|---------|-------------|
| 本文行数 | 200 行以上 | coverage-check.py |
| `[REF:]` 数 | 10 件以上 | coverage-check.py |
| fenced code block | 3 個以上 | coverage-check.py |
| Mermaid 図 | 1 個以上 | coverage-check.py |
| Sources Read 項目 | 5 件以上 | coverage-check.py |

これを満たさない章は Phase 4 で reject され、Phase 3 に戻ってループバック修正が必要。

各 `[REF: ...]` の前後に「何が起きているか」を解説する文章を書く。
RailsやLaravelのようなフレームワークの「典型挙動」だけで埋めるのは禁止。**実コードを読んだ結果**を書くこと。

#### STEP D: 不確実性マーカー

各記述の不確実性を明示する:
- `[CONFIDENCE: HIGH | MED | LOW]`
- `[ASK SME]`（業務有識者への確認が必要）
- `[ASSUMED: ...]`（推測の根拠）

#### STEP E: 詳細疑問の Question Bank 追加

章執筆中に湧いた疑問を `questions.json` に追加（最低 1 章につき 1 件）。
最終的に `questions.json` は **10 件以上** あることが要件（`coverage-check.py` が検査）。

例:
- このメソッドが3回リトライする理由は技術的制約か業務要件か
- この設定値の根拠は何か
- このコメントアウトされたコードは過渡期の名残か仕様か

#### STEP F: critical な疑問への対応

critical な疑問にぶつかった場合、当該節を `[BLOCKED: see Q-042]` として空欄で残す。
Phase 5 で対話解決後に Phase 3 へループバックして埋める。

#### STEP G: 章ごとのサブエージェント delegation（task ツール利用可能時、推奨）

`task` ツール(または同等のサブエージェント呼び出し機構)が利用可能な環境では、**各章を独立サブエージェント `chapter-investigator`(`agents/chapter-investigator.md` 参照)に委譲**してください。メインエージェントが全章を直接書くと文脈が劣化するため、章ごとに独立コンテキストで深く調査する方が品質が高くなります。

**サブエージェント呼び出しテンプレ:**

```
task(
  description="ch05 data-model investigation",
  prompt=\"\"\"
あなたは Chapter 5: データモデル を担当する chapter-investigator です。

対象 inventory_ids:
- INV-012 (Project)
- INV-013 (Issue)
- INV-014 (User)
- INV-015 (Role)

対応する実ソース（必ず file_editor view で読んでください）:
- redmine-master/app/models/project.rb
- redmine-master/app/models/issue.rb
- redmine-master/app/models/user.rb
- redmine-master/app/models/role.rb
- redmine-master/db/schema.rb（関連箇所）

ドラフト出力先: .cc-rsg/drafts/05-data-model.md

目標品質:
- 本文 200 行以上
- [REF: path:Lstart-Lend] を 10 件以上
- fenced code block 3 個以上
- Mermaid 図 1 個以上（ER 図）
- ## Sources Read セクションに 5 ファイル以上

完了したら章の主要ポイント + 詳細疑問リストを返してください。
詳細疑問は questions.json に追記する素材です。
\"\"\",
  subagent_type="chapter-investigator"
)
```

**重要な制約**:

- **逐次実行（並列度1）**: OpenHands SDK の TaskManager は内部で `threading.Lock` により1つずつ実行する。13章なら 13 回の `task` 呼び出しが順番に走る。**所要時間は短縮されない**が、章ごとの独立コンテキストで品質が向上する。
- **プロンプトキャッシュは共有されない**: 各サブエージェントは独立 LLM context を持つため、メインの 5〜10 倍のトークン消費。ChatGPT Plus サブスクリプションでは上限到達が早いので、**Anthropic API / OpenAI API モード推奨**。
- **章ドラフトは サブエージェント側が直接 `file_editor` で書く**（戻り値テキストではなくファイルとして保存）。メインは戻り値を読んで questions.json に詳細疑問を追記する役割。
- **章ごとに 1 回ずつ起動**。全章をまとめて 1 task に渡すと意味がない（独立コンテキストの恩恵が消える）。

**task ツールが利用できない環境**では、STEP A〜F の手順をメインエージェントが章ごとに自分で実施する（サブエージェント委譲なしの動作）。

### このフェーズで気を付けること
- **コードを読まずに章を書くのは禁止**。これは Phase 3 の最重要原則。
- Sources Read セクションに列挙したファイルしか参照してはいけない。
- 章間の整合性は Phase 4 で検証する。
- 不確実性マーカーは隠蔽せず、ドラフトに明示的に残す。これが Phase 5 対話の出発点になる。

---

## Phase 4: Verify(検証 + ループバック)

### 目的
インベントリ照合、章品質メトリクス、MECE 検査、整合性検査を自動実行し、不合格章を Phase 3 にループバックさせる。

### 動作手順

1. **trace.json の生成**
   ```bash
   python .cc-rsg/skill/scripts/build-trace.py --cc-rsg-dir .cc-rsg --target-dir-for-required drafts
   ```
   これで drafts/*.md 内の `[REF: path:line]` を全件 SRC ユニットに解決し、MECE 集計が出る。

2. **coverage-check.py の実行**
   ```bash
   python .cc-rsg/skill/scripts/coverage-check.py \
     --cc-rsg-dir .cc-rsg \
     --target-dir-for-required drafts \
     --output-format text
   ```
   以下を一括検査する:
   - inventory 件数（min: max(50, files/20)）
   - macro 型 INV 比率（上限 20%）
   - covered_by 充填率（90%）
   - 各章の本文行数（200 行+）、`[REF:]` 数（10+）、コードブロック（3+）、Mermaid（1+）、Sources Read 項目（5+）
   - questions 件数（10+）、open 比率（上限 20%）
   - MECE カバレッジ（70%+）

3. **不合格 → Phase 3 ループバック**
   - exit code が 1 のとき、出力された「ゲート判定」セクションを読んで:
     1. 不合格章を特定（例: `章 05-data-model.md: [REF:] が 7 個 < 10 個必要`）
     2. その章の `assigned_inventory_ids` に対応するソースを **追加 view**
     3. Sources Read に追加し、`[REF:]` を増やし、本文を厚くする
     4. 再度 coverage-check.py を実行
   - 最大反復回数: **3**。3回でも PASS しない章は `99-unresolved.md` に「品質不足」として記録し、後段に進む。

4. **クロスリファレンス検証**
   - 章間で同一概念に対する記述が矛盾していないかチェック。
   - 矛盾は `questions.json` に `priority: critical` で追加。

5. **疑問の正規化（deduplication）**
   - Question Bank 全体に対して重複検出を実施。
   - 「明らかに同一」のみ自動マージ、「似ているが微妙に違う」はグループ化フラグを立てて Phase 5 で確認。

6. **検証レポートの保存**
   - `coverage-check.py --output-format json` の結果を `.cc-rsg/coverage-report.json` に保存。
   - 人間可読版を `.cc-rsg/coverage-report.md` に保存。

7. **Phase 4完了**
   - 全章 PASS（または 3 回試行後の質的限界到達）で `state.json` を更新し、Phase 5 へ進む。

### このフェーズで気を付けること
- **coverage-check.py が PASS するまで Phase 5 へ進んではならない**（最大3反復ループ）
- ループバックは「単に文章を水増しする」ことではない。**実コードを追加で読み、引用を増やし、説明を厚くする** ことが目的。
- 章間矛盾を見逃すと Phase 5 の対話量が爆発する。Phase 4 で潰す。

---

## Phase 5: Refine via Dialogue(対話による精緻化)

### 目的
利用者との対話で不確実性マーカーと Question Bank を解消し、仕様書を精緻化する。

### 3 段階すべて必須

`coverage-check.py` で `--max-open-ratio 0.2` を強制しているため、open のまま 20% を残すと Phase 6 に進めない。3 段すべて実施する。

#### 第1段: 全体像提示（必須・1回）

`ask_user_question` で **1問** だけ提示:

```
未解決疑問の総数: N 件
カテゴリ別内訳: 業務ルール X 件、アーキテクチャ Y 件、データモデル Z 件、…
優先度別内訳: critical X 件、important Y 件、nice-to-have Z 件

進行モードを選択してください:
- すべての疑問に1件ずつ回答する（最も丁寧）
- critical のみ回答する（時間短縮）
- 推測で全部 abandoned にして Phase 6 へ（最速・品質低下）
```

choices: `["すべて回答", "critical のみ", "推測で省略"]`、allow_free_text: true

#### 第2段: critical クラスタ提示（必須・最低 3 クラスタ）

第1段で「すべて」または「critical のみ」を選んだ場合、critical な疑問を関連クラスタにまとめて提示。
**最低 3 クラスタ** を作成（クラスタが足りない場合は中粒度で分割）。

各クラスタは `ask_user_question` で1問として提示:
```
業務ルールクラスタ A（#Q-005, #Q-008, #Q-012）
これらは購入フロー周辺の疑問です。
連続して回答しますか？

- 連続回答する（推奨）
- このクラスタは後回し
- このクラスタは全部 abandoned
```

#### 第3段: 個別対話（残り全疑問）

各疑問について `ask_user_question` で個別提示:

- **question**: 該当コード抜粋 + 暫定仮定 + リスク
- **choices**: `["推測でOK（仕様書に反映）", "正解を入力", "SMEに確認が必要なのでスキップ", "永遠に確定できない（abandoned）"]`
- **allow_free_text**: true

回答を `questions.json` の各エントリに反映:
- `推測でOK` → `status: answered`, `answer: <暫定推測>`
- `正解を入力` → `status: answered`, `answer: <ユーザー自由入力>`
- `SMEに確認が必要` → `status: skipped`
- `abandoned` → `status: abandoned`

### Phase 5 で agent が「水増し」しないために

**questions.json が 10 件未満の場合**:
- Phase 3 のドラフトレビューで「アンビギュアスな箇所」を最低 5 件抽出し、questions.json に追加してから Phase 5 を開始する。
- 抽出観点:
  - 命名規則や設計意図が曖昧な箇所
  - ビジネスルールが推測でしか書けない箇所
  - エラーハンドリング方針が複数解釈可能な箇所
  - フレームワーク標準と異なる特殊実装の意図
  - 未使用コード / 廃止予定コードの扱い

### 回答の反映

- 各回答を該当する章ドラフトに反映（不確実性マーカーを除去 or 更新）
- `[BLOCKED: see Q-NNN]` 節を本文で埋める

### 再偵察（必要時のみ）

回答内容により新たな調査が必要になった場合、Phase 3 の追加ステップとして実コードを再度 view し、章を更新。

### Phase 5 完了判定

`coverage-check.py` の `--max-open-ratio 0.2` 基準を満たす:
- 全疑問の少なくとも 80% が `answered` / `skipped` / `abandoned` のいずれか
- `open` のまま残るのは 20% 未満
- これを満たすまで Phase 5 を継続。

### このフェーズで気を付けること
- 第1段・第2段をスキップして第3段だけ実施するのは禁止（利用者が全体像を掴めない）
- 全疑問に SME レベルの正解を求めると対話が破綻する。`nice-to-have` は推測のままで進めることを許容する
- `abandoned` は本物の「答えが永遠に出ない」ものに限る（労力削減のための濫用禁止）

---

## Phase 6: Deliver(納品)

### 目的
最終成果物として仕様書一式を`.cc-rsg/final/`配下にMarkdownで出力する。

### 動作手順

ファイル名は Phase 2 で確定済みの ASCII slug 規約(`^(0\d|[1-9]\d)-[a-z0-9-]+\.md$`、予約ファイル: `00-metadata.md` / `99-unresolved.md` / `traceability.md`)に従う。Phase 6 では新規命名は行わず、Phase 2 で生成済みのスケルトンに本文を充填する。

1. **章ドラフトの統合**
   - `drafts/`配下の各章を `.cc-rsg/final/` にコピーし、テンプレートで定義された順序で並べる。
   - ファイル名は変更しない(Phase 2 確定の ASCII slug 名をそのまま使用)。
   - 各章ファイル冒頭のメタコメントは除去する。

2. **トレーサビリティ表の生成(`traceability.md` への充填)**
   - Phase 2 で空ファイルとして生成済みの `traceability.md` に本文を書き込む。
   - 仕様書の各章・節と、参照したソースコードの対応表を生成する。
   - 形式例:

   ```markdown
   | 仕様書セクション | 参照元 |
   |----------------|--------|
   | 3.2 ユーザー無効化 | src/jobs/UserDeactivationJob.php:12-58 |
   ```

3. **「未確定事項」章の生成(`99-unresolved.md` への充填)**
   - Phase 2 で空ファイルとして生成済みの `99-unresolved.md` に本文を書き込む。
   - `questions.json` の `abandoned` ステータスの疑問を集約する。
   - 各未確定事項について「なぜ確定できなかったか」「現時点でどこまで推測したか」「将来確定するために何が必要か」を記載する。
   - 章本文タイトルは `goal.json.output_language` に従う(日本語例: 「第99章: 未確定事項」/ 英語例: `Chapter 99: Unresolved Items`)。ファイル名 `99-unresolved.md` は言語に関わらず固定。

4. **メタデータの生成(`00-metadata.md` への充填)**
   - Phase 2 で空ファイルとして生成済みの `00-metadata.md` に本文を書き込む。
   - 含める内容: 生成日時、対象コードベースのコミットハッシュ(取得可能なら)、Phase 0 で確定したゴール定義、テンプレート選定結果、cc-rsg バージョン。

5. **最終成果物のレイアウト**
   ```
   .cc-rsg/final/
   ├── 00-metadata.md       # メタデータ(Phase 2 で生成、Phase 6 で充填)
   ├── 01-overview.md       # 第1章: 概要
   ├── 02-architecture.md   # 第2章: アーキテクチャ
   ├── 03-...各章...md
   ├── 99-unresolved.md     # 未確定事項(Phase 2 で生成、Phase 6 で充填)
   ├── traceability.md      # トレーサビリティ表(Phase 2 で生成、Phase 6 で充填)
   └── README.md            # 成果物の読み方ガイド(Phase 6 で生成)
   ```
   注: ファイル名は ASCII slug 固定(言語非依存)。本文章タイトルは `goal.json.output_language` に従う(日本語例: `# 第1章: 概要` / 英語例: `# Chapter 1: Overview`)。

6. **完了通知**
   - 利用者に成果物の所在と総ページ数(またはセクション数)、解決済み疑問数、未確定事項数を報告する。
   - `state.json`を完了状態にする。

### このフェーズで気を付けること
- 「未確定事項」章(`99-unresolved.md`)を省略してはならない。仕様書の信頼性を担保する根幹である。
- メタデータ章(`00-metadata.md`)を省略すると、後で「いつ、どのバージョンのコードから生成したか」が不明になる。
- トレーサビリティ表(`traceability.md`)を省略すると、各記述の根拠が辿れなくなる。
- 必須3ファイル(`00-metadata.md` / `99-unresolved.md` / `traceability.md`)の存在は `scripts/coverage-check.py` で検証される。欠落していれば error として報告される。

---

## Question Bank の運用

### データ構造

`.cc-rsg/questions.json`に蓄積される各疑問エントリは以下のフィールドを持つ。

```json
{
  "id": "Q-042",
  "generated_at_phase": "investigation",
  "category": "business_rule",
  "body": "この決済処理が3回リトライする理由は技術的制約か業務要件か",
  "evidence": {
    "file": "src/payment/PaymentRetryHandler.php",
    "lines": "45-58",
    "code_excerpt": "for ($i = 0; $i < 3; $i++) { ... }"
  },
  "related_inventory_ids": ["INV-027"],
  "severity": "important",
  "resolution_type": "ask_sme",
  "status": "open",
  "answer": null,
  "answerer": null,
  "answered_at": null,
  "related_question_ids": []
}
```

### 7標準カテゴリ

1. **business_rule**: 業務ルール
2. **architecture_decision**: アーキテクチャ判断
3. **data_model_intent**: データモデル意図
4. **external_integration**: 外部システム連携
5. **naming_history**: 命名・歴史的経緯
6. **operational_requirement**: 運用要件
7. **security_compliance**: セキュリティ・コンプライアンス

利用者は必要に応じてカスタムカテゴリを追加できる(初版では手動でJSONを編集する想定。UIは将来拡張)。

### 深刻度レベル

- **critical**: この疑問が解消されないと章が書けない。サブエージェントは当該節を空欄(`[BLOCKED]`)で残す。
- **important**: 推測で書けるが、確度が低い。`[CONFIDENCE: LOW]`マーカーを残す。
- **nice-to-have**: 細部の精緻化に関わる疑問。推測で書き、Phase 5で軽く確認する。

### ステータス遷移

```
open → asked → answered
            ↓
            abandoned
```

---

## サブエージェントの動作

### サブエージェントへのプロンプトテンプレート(スケルトン)

Phase 3でTaskツールに渡すプロンプトの骨格は以下の通り。詳細は段階2で `references/subagent-prompt.md` として外出しする。

```
あなたは仕様書の特定章を担当する調査エージェントです。

[ゴール定義(goal.jsonから抜粋)]
- 出力言語 / Output language: {output_language}  ("en" または "ja")
- 主たる読者: {primary_reader}
- 粒度希望: {granularity}
- 重視観点: {perspectives}

[出力言語の取り扱い]
- 章本文、見出し、本文中の説明、不確実性マーカーの注釈テキスト、章末尾の詳細疑問リスト本文は すべて {output_language} で記述する。
- 機械可読要素 — ファイル名(ASCII slug)、`[REF: file:lines]`、`[CONFIDENCE: HIGH|MED|LOW]`、`[ASK SME]`、`[ASSUMED: ...]`、`[BLOCKED: see Q-XXX]`、ID(`Q-XXX` / `INV-XXX`) — は言語非依存のまま英語固定。
- 参照資料(`templates/*.md`、`references/*.md`)が日本語で記述されている場合でも、{output_language} == "en" であれば章見出し例・本文サンプル等を意味的に等価な英語に翻訳した上で章本文を生成する。

[担当章]
- 章タイトル: {chapter_title}
- 章で扱うべきインベントリ項目: {inventory_ids}
- テンプレート定義(該当章の構造): {template_section}

[作業指示]
1. 担当インベントリ項目に対応するソースコードを精読する。
2. 章本文を生成する。
3. 各記述には [REF: file:lines] 形式で行番号付き参照を付ける。
4. 不確実性は隠蔽せず、以下マーカーを使用する。
   - [CONFIDENCE: HIGH | MED | LOW]
   - [ASK SME]
   - [ASSUMED: 推測内容; 根拠: ...]
   - [BLOCKED: criticalな疑問のため空欄]
5. 章末尾に「この章で発生した詳細疑問」リストを付与する。

[制約]
- 推測と事実を混同しない。
- ゴール定義の粒度を超えた詳細記述はしない。
- criticalな疑問にぶつかった場合は当該節を [BLOCKED] として残し完了報告する。

[出力フォーマット]
{詳細は references/subagent-prompt.md を参照}
```

### サブエージェントの判断ロジック

疑問にぶつかった際、サブエージェントは以下の擬似コードで動作する。

```
if 疑問のseverity == "critical":
    当該節を [BLOCKED: see Q-XXX] として残す
    Question Bankに登録
    章の他の節は可能な限り完成させる
    完了報告
else:
    [CONFIDENCE: LOW; ASSUMED: 推測内容] マーカーを残す
    推測でベストエフォートで章を完成
    Question Bankに登録
    完了報告
```

---

## 状態管理と再開

### 状態ファイル `state.json` の構造

```json
{
  "current_phase": 3,
  "phase_progress": {
    "phase_3": {
      "total_subtasks": 12,
      "completed_subtasks": 8,
      "blocked_subtasks": ["chapter_payment", "chapter_auth"]
    }
  },
  "started_at": "2026-05-01T10:00:00+09:00",
  "last_updated": "2026-05-01T14:32:15+09:00",
  "session_history": [
    {"timestamp": "2026-05-01T10:00:00+09:00", "phase": 0, "event": "started"},
    {"timestamp": "2026-05-01T10:15:00+09:00", "phase": 1, "event": "transitioned"}
  ]
}
```

### 再開時の動作

スキル起動時に既存の`.cc-rsg/state.json`を検出した場合、以下メッセージで利用者に状況を報告し意図確認する。なお、`.cc-rsg/goal.json` が読み込めればその `output_language` でメッセージを出力する。`goal.json` 自体が欠落しているなど言語不明の場合のみ、Phase 0 手順3と同じくバイリンガル(英語/日本語併記)で表示してから言語選択を促す。

**再開メッセージのテンプレート例(日本語版 / `output_language: "ja"`)**:

```
前回のセッションで cc-rsg を実行しています。状況は以下の通りです。

- 現在のフェーズ: Phase 3 (Investigate)
- 進捗: 12サブタスク中8件完了、2件は critical な疑問により BLOCKED 状態
- Question Bank: 未解決疑問 23件(うち critical: 2件)
- 最終更新: 2026-05-01 14:32

以下のいずれを実施しますか?
(A) 続きから再開(Phase 3 残タスクを完了させる)
(B) Phase を巻き戻す(指定する Phase から再開)
(C) 全リセット(.cc-rsg/ を削除して Phase 0 から開始)
(D) 状況を詳細表示してから判断する
```

各Phaseごとの再開メッセージ詳細は段階2で別ドキュメント化する。

---

## 参照ドキュメントとテンプレート

このスキルは以下の参照ドキュメントとテンプレートに依存する。実体は段階2で作成される。

### `references/`配下

- `references/inventory-units.md`: 言語・フレームワーク別のインベントリ単位定義(PHP, COBOL, Python, Java, JavaScript/TypeScript, C#等)
- `references/template-catalog.md`: テンプレート選定のガイド
- `references/question-categories.md`: Question Bank 7標準カテゴリの詳細とカスタムカテゴリ追加方法
- `references/verification-checklists.md`: Phase 4で使う検証チェックリスト
- `references/subagent-prompt.md`: Phase 3で使うサブエージェントプロンプトの完全版

### `templates/`配下

- `templates/web-app.md`: Webアプリケーション仕様書テンプレート
- `templates/batch-system.md`: バッチ処理システム仕様書テンプレート
- `templates/api-service.md`: APIサービス仕様書テンプレート
- `templates/library-sdk.md`: ライブラリ/SDK仕様書テンプレート

### `scripts/`配下

- `scripts/coverage-check.py`: `inventory.json`と`drafts/`配下のMarkdownを照合し未言及項目をリスト化する検証スクリプト

---

## ファイルレイアウト

### スキル本体(配布時)

```
.claude/skills/cc-rsg/
├── SKILL.md                          (このファイル)
├── references/
│   ├── inventory-units.md
│   ├── template-catalog.md
│   ├── question-categories.md
│   ├── verification-checklists.md
│   └── subagent-prompt.md
├── templates/
│   ├── web-app.md
│   ├── batch-system.md
│   ├── api-service.md
│   └── library-sdk.md
└── scripts/
    └── coverage-check.py
```

### 利用プロジェクト側の作業ディレクトリ

```
.cc-rsg/
├── state.json          (現在のフェーズと進捗)
├── goal.json           (Phase 0の回答)
├── recon-report.md     (Phase 1の偵察結果)
├── inventory.json      (全インベントリ項目)
├── wbs.json            (Phase 2の作業分解)
├── questions.json      (Question Bank)
├── drafts/             (各章のドラフトMarkdown、ファイル名は ASCII slug 規約)
│   ├── 00-metadata.md      # Phase 2 で空生成、Phase 6 で充填
│   ├── 01-overview.md
│   ├── 02-architecture.md
│   ├── ...
│   ├── 99-unresolved.md    # Phase 2 で空生成、Phase 6 で充填
│   └── traceability.md     # Phase 2 で空生成、Phase 6 で充填
└── final/              (最終成果物、drafts と同じファイル名)
    ├── 00-metadata.md
    ├── 01-overview.md
    ├── ...
    ├── 99-unresolved.md
    ├── traceability.md
    └── README.md
```

---

## 実装上の重要原則

### 正直さを最優先とする
綺麗で完成度の高い仕様書よりも、正直で穴が見えている仕様書のほうが実務的価値が高い。Claudeが推測した部分とコードから確実に言える部分を明確に区別し、`abandoned`疑問は「未確定事項」として明示する。

### トレーサビリティを担保する
各記述がソースコードのどの位置に由来するかを必ず行番号付きで追跡可能にする。これはKDM(Knowledge Discovery Metamodel)のSourceパッケージ思想を継承するものであり、メンテナンス担当者が後から検証できる仕様書の必須要件である。

### 段階的詳細化を尊重する
最初から完璧な仕様書を狙わない。Phase 1で全体像、Phase 2で骨格、Phase 3で章ドラフト、Phase 5で精緻化、と段階を踏む。各段階で利用者レビューを挟む。

### 再開可能性を保証する
長時間にわたる解析セッションで進捗・既知の事実・未解決の疑問をファイルシステムに記録し、いつでも中断・再開できるようにする。Reversaの`.reversa/state.json`思想を継承する。

---

## 想定されるトラブルとその対処

### コードベースが大きすぎてPhase 1偵察が完了しない
- 対象範囲を明示的に絞る(モノリポの特定モジュール等)。
- Phase 0のゴール定義5問で「対象範囲」も追加で確認する運用を検討。

### サブエージェント並列実行で context が肥大化する
- 1サブエージェント=1章を原則とし、章をさらに細分化することで個々のcontextを小さく保つ。
- 共通参照(`goal.json`, `inventory.json`の関連抜粋)のみ渡し、無関係なファイルは渡さない。

### Question Bankが膨大になり対話が破綻する
- Phase 4の正規化で重複疑問をマージする。
- 深刻度フィルタを使い、まず critical のみ対話する。

### 利用者がレビューに時間を割けない
- 各Phase完了時のレビューは「承認するだけで進む」設計とする。
- 詳細レビューを後回しにしてPhase 6まで進め、最終成果物に対して一括レビューする運用も許容する。

---

## バージョンと変更履歴

- v0.2.0 (2026-06-06): 大規模 Ruby on Rails コードベース(1095ファイル規模)への実戦投入フィードバックを反映した大型強化。Phase 3 を STEP A〜G (Sources Read → 引用抽出 → 章執筆 → 不確実性 → 詳細疑問 → critical 対応 → サブエージェント委譲) に再構成。Phase 4 にループバック検証 (MECE / カバレッジ / 最小行数 / 最小 REF 数 / Mermaid 数 / Question Bank 整合性等 11 種) を追加。Phase 5 を 3 段階 (全体像 / critical クラスタ / 個別対話) 必須化、回答水増し防止規定を追加。inventory-units.md に粒度規定と Rails 用カタログ (14 単位) を追加。出力言語選択にデフォルト方針 (`"ja"`) を追加。`scripts/` に `build-trace.py` / `build-traceability.py` / `source-map.py` を追加、`coverage-check.py` を 11 項目検証に拡張。`agents/chapter-investigator.md` を新規追加 (章単位サブエージェント定義)。
- v0.1.0 (2026-05-01): 初版ドラフト作成。Phase 0〜6の状態マシン、Question Bank、サブエージェント動作、ファイルレイアウトを定義。

---

## ライセンスと公開

MIT License。OSSとして公開する前提で設計されている。

`cc-sdd`(Spec Driven Development)の対概念として、コミュニティでの認知を意図したネーミング。SDDがforward(仕様→コード)、RSGがreverse(コード→仕様)。
