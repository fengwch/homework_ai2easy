//go:build wireinject
// +build wireinject

package main

import (
	"github.com/google/wire"
	"github.com/go-kratos/kratos/v2"
	"github.com/go-kratos/kratos/v2/log"

	"homework_ai2easy/backend/internal/conf"
	"homework_ai2easy/backend/internal/data/dao"
	"homework_ai2easy/backend/internal/biz/usecase"
	grpcService "homework_ai2easy/backend/internal/service/grpc"
	"homework_ai2easy/backend/internal/server"
	pkgProvider "homework_ai2easy/backend/internal/pkg"
)

// wireApp init kratos application.
func wireApp(cs *conf.Server, cd *conf.Data, cj *conf.JWT, csms *conf.SMS, cai *conf.AiAgent, cwechat *conf.Wechat, logger log.Logger) (*kratos.App, func(), error) {
	panic(wire.Build(
		dao.ProviderSet,
		pkgProvider.ProviderSet,
		usecase.ProviderSet,
		grpcService.ProviderSet,
		server.ProviderSet,
		newApp,
	))
}
