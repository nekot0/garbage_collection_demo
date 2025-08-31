# Single Agent - 粗大ごみ収集申込システム

このプロジェクトは、自治体の粗大ごみ収集申込を支援するAIエージェントシステムです。LangChainとStreamlitを使用して、ユーザーとの対話を通じて必要な情報を収集し、申込手続きを完了させます。

## 主な機能

- **対話型申込**: ユーザーと自然な会話で粗大ごみ収集の申込情報を収集
- **複数LLMプロバイダー対応**: Azure OpenAI、OpenAI、AWS Bedrockをサポート
- **日本語日付処理**: 「来週金曜」などの相対日付を自動解釈
- **料金自動計算**: 品目に応じた収集料金の概算表示
- **収集可能日チェック**: 指定日時が収集可能かの自動判定
- **Web UI**: Streamlitベースの使いやすいチャットインターフェース

## システム構成

```
single_agent/
├── agents/                    # エージェント関連
│   ├── common/               # 共通モジュール
│   │   ├── llm_factory.py   # LLMプロバイダー設定
│   │   └── tools.py         # 業務ツール関数
│   └── garbage/             # 粗大ごみ専用エージェント
│       ├── agent.py         # メインエージェントロジック
│       ├── prompts.py       # プロンプトテンプレート
│       └── schema.py        # データ構造定義
├── memory/                   # データ永続化
│   └── store.py             # インメモリストア（デモ用）
├── orchestrator/            # ルーティング
│   └── router.py            # エージェント振り分け
├── ui/                      # ユーザーインターフェース
│   └── streamlit_app.py     # Webアプリケーション
└── tests/                   # テストコード
```

## 技術スタック

- **Python 3.9+**
- **LangChain**: エージェントフレームワーク
- **Streamlit**: Webインターフェース
- **Pydantic**: データバリデーション
- **python-dateutil**: 日付処理
- **pytest**: テストフレームワーク

## インストールと設定

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env`ファイルを作成し、使用するLLMプロバイダーに応じて設定：

#### Azure OpenAI使用時
```bash
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
```

#### API Gateway使用時
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=api_gateway_access_point
OPENAI_MODEL=google/gemma-3-12b-it
```

#### AWS Bedrock使用時
```bash
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=xx.meta.llama3-1-8b-instruct-v1:0
AWS_REGION=region
```

### 3. アプリケーション起動

```bash
PYTHONPATH=$(pwd) streamlit run ui/streamlit_app.py
```

## 使用方法

1. Webブラウザで `http://localhost:8501` にアクセス
2. 「新しいスレッドを作成」ボタンをクリック
3. チャット画面で申込内容を入力（例：「来週火曜にソファ1点を自宅前で回収してほしい」）
4. エージェントが不足情報を順次質問
5. 全情報が揃うと申込内容を確認表示
6. 「はい」で予約完了

## エージェント機能詳細

### 情報収集項目
- **お名前**: カタカナ氏名
- **ご住所**: 市区町村〜番地
- **お電話番号**: 数字のみ
- **回収物の品目**: ソファ、マットレス等
- **個数**: 半角数字
- **希望日**: YYYY-MM-DD形式または相対日付
- **時間帯**: 午前/午後
- **回収場所**: 自宅前/集合所等

### 対話の流れ
1. **情報抽出**: ユーザー発話から申込情報を構造化
2. **不足項目質問**: 優先度順に1項目ずつ質問
3. **日付正規化**: 相対日付を具体的な日付に変換
4. **収集可能性チェック**: 日曜・祝日等の制限確認
5. **料金計算**: 品目・個数に応じた概算表示
6. **最終確認**: 申込内容のレビューと承認
7. **予約完了**: 受付番号の発行

## テスト実行

```bash
pytest tests/
```

## 今後の拡張予定

- データベース連携（現在はインメモリ）
- 複数エージェント対応（引越し、不用品買取等）
- API連携（実際の収集システム）
- 多言語対応
- 音声インターフェース

## ライセンス

LICENSEファイルを参照ください。

