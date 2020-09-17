# セットアップ

.env.exampleをコピーして各環境に合うように適宜書き換える。

```shell script
cp .env.example .env
```

# デプロイ環境の立ち上げ

docker-compose.ymlは必要がなければ書き換える必要なし。

```shell script
docker-compose up -d
```

# デプロイ

コンテナ内でdeploy.shを実行させ、CDKのデプロイを実行する。

デプロイするStackを指定したい時、Stack名を変えたときはdeploy.shを適宜書き換える。

※初期内容は全Stackを個別にデプロイしている。

```shell script
docker-compose exec aws-cdk sh -c 'sh deploy.sh' 
```

# デストロイ

コンテナ内でdeploy.shを実行させ、CDKのデストロイを実行する。

deploy.shの初期内容は全Stackをデストロイする仕様になっているので、必要に応じて書き換える。

```shell script
docker-compose exec aws-cdk sh -c 'sh destroy.sh'
```