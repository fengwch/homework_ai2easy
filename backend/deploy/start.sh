#!/bin/bash
# Homework AI2Easy 后端启动脚本
# 使用方式: ./start.sh 或 nohup ./start.sh > logs/console.log 2>&1 &

cd "$(dirname "$0")"

CONF="${CONF:-configs/config.yaml}"
if [ ! -f "$CONF" ]; then
  echo "错误: 配置文件 $CONF 不存在"
  echo "请复制 config.example.yaml 为 config.yaml 并修改配置"
  exit 1
fi

mkdir -p logs uploads
exec ./bin/server -conf "$CONF"
