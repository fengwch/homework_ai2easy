# 获取 GOPATH
GOPATH := $(shell go env GOPATH)
BIN_DIR := $(GOPATH)/bin

.PHONY: init
init:
	@echo "检查并安装必要的工具..."
	@if [ ! -f "$(BIN_DIR)/protoc-gen-go" ]; then \
		echo "安装 protoc-gen-go..."; \
		go install google.golang.org/protobuf/cmd/protoc-gen-go@latest; \
	else \
		echo "protoc-gen-go 已存在于 $(BIN_DIR)"; \
	fi
	@if [ ! -f "$(BIN_DIR)/protoc-gen-go-grpc" ]; then \
		echo "安装 protoc-gen-go-grpc..."; \
		go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest; \
	else \
		echo "protoc-gen-go-grpc 已存在于 $(BIN_DIR)"; \
	fi
	@if [ ! -f "$(BIN_DIR)/kratos" ]; then \
		echo "安装 kratos..."; \
		go install github.com/go-kratos/kratos/cmd/kratos/v2@latest; \
	else \
		echo "kratos 已存在于 $(BIN_DIR)"; \
	fi
	@if [ ! -f "$(BIN_DIR)/protoc-gen-go-http" ]; then \
		echo "安装 protoc-gen-go-http..."; \
		go install github.com/go-kratos/kratos/cmd/protoc-gen-go-http/v2@latest; \
	else \
		echo "protoc-gen-go-http 已存在于 $(BIN_DIR)"; \
	fi
	@if [ ! -f "$(BIN_DIR)/wire" ]; then \
		echo "安装 wire..."; \
		go install github.com/google/wire/cmd/wire@latest; \
	else \
		echo "wire 已存在于 $(BIN_DIR)"; \
	fi
	@echo "工具检查完成！"

.PHONY: api
api:
	@echo "生成 API 代码..."
	@export PATH=$(BIN_DIR):$$PATH; \
	find api -name *.proto | xargs -I {} protoc --proto_path=./api \
		--proto_path=./third_party \
		--go_out=paths=source_relative:./api \
		--go-http_out=paths=source_relative:./api \
		--go-grpc_out=paths=source_relative:./api \
		--openapi_out=fq_schema_naming=true,default_response=false:. {}
	@echo "生成配置代码..."
	@export PATH=$(BIN_DIR):$$PATH; \
	protoc --proto_path=./internal/conf \
		--proto_path=./third_party \
		--go_out=paths=source_relative:./internal/conf \
		./internal/conf/conf.proto

.PHONY: tidy
tidy:
	@echo "整理 Go 模块依赖..."
	go mod tidy
	@echo "依赖整理完成！"

.PHONY: wire
wire: api
	@echo "生成 Wire 依赖注入代码..."
	@export PATH=$(BIN_DIR):$$PATH; \
	cd cmd/server && wire
	@echo "Wire 代码生成完成！"

.PHONY: build
build: tidy wire
	@echo "编译项目..."
	@mkdir -p bin
	@VERSION=$$(git describe --tags --always --dirty 2>/dev/null || echo "dev"); \
	go build -ldflags "-X main.Version=$$VERSION" -o ./bin/server ./cmd/server
	@echo "编译完成！可执行文件: ./bin/server"

.PHONY: build-fast
build-fast:
	@echo "快速编译（跳过 tidy 和 wire）..."
	@mkdir -p bin
	@VERSION=$$(git describe --tags --always --dirty 2>/dev/null || echo "dev"); \
	go build -ldflags "-X main.Version=$$VERSION" -o ./bin/server ./cmd/server
	@echo "编译完成！可执行文件: ./bin/server"

.PHONY: test
test: test-unit test-api
	@echo "全部测试完成！"

.PHONY: test-unit
test-unit:
	@echo "运行单元测试 (biz/usecase, testutil, pkg)..."
	go test -v ./internal/biz/usecase/... ./internal/pkg/... -count=1

.PHONY: test-api
test-api:
	@echo "运行接口测试 (auth HTTP API)..."
	go test -v ./test/... -count=1

.PHONY: test-short
test-short:
	@echo "快速测试（无 -v）..."
	go test ./... -count=1

.PHONY: run
run: build
	@echo "启动服务..."
	./bin/server

.PHONY: dev
dev: wire
	@echo "开发模式运行（直接运行，不编译）..."
	go run ./cmd/server

.PHONY: pack
pack:
	@./scripts/pack-deploy.sh

.PHONY: clean
clean:
	@echo "清理构建产物..."
	rm -rf bin/
	rm -rf api/*.go
	rm -rf api/*/*.go
	@echo "清理完成！"

.PHONY: all
all: tidy build run
