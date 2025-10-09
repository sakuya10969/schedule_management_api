## Azure Container Appsへ反映させる方法

### ソースコード変更後、コンテナをビルド
```
docker-compose build --no-cache
```

### Azure && ACRへログイン
```
az login
az acr login --name smdev
```

### ACRへイメージをプッシュ
```
docker-compose push
or
docker push smdev.azurecr.io/schedule_management_api:latest
```

### AZ CLIでACAのリビジョンを更新
```
az containerapp update \
  --name ca-sm-dev-010 \
  --resource-group funcsche \
  --image smdev.azurecr.io/schedule_management_api:latest \
  --revision-suffix rev-YYMMDD
```
