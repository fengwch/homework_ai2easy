package main

import (
	"flag"
	"os"

	"github.com/go-kratos/kratos/v2"
	"github.com/go-kratos/kratos/v2/config"
	"github.com/go-kratos/kratos/v2/config/file"
	"github.com/go-kratos/kratos/v2/log"
	"github.com/go-kratos/kratos/v2/transport/grpc"
	"github.com/go-kratos/kratos/v2/transport/http"

	_ "go.uber.org/automaxprocs"

	"homework_ai2easy/backend/internal/conf"
	"homework_ai2easy/backend/internal/pkg/apilist"
	"homework_ai2easy/backend/internal/pkg/logger"
)

// go build -ldflags "-X main.Version=x.y.z"
var (
	// Name is the name of the compiled software.
	Name = "homework-ai2easy"
	// Version is the version of the compiled software.
	Version = "v1.0.0"
	// flagconf is the config flag.
	flagconf string

	id, _ = os.Hostname()
)

func init() {
	flag.StringVar(&flagconf, "conf", "configs/config.yaml", "config path, eg: -conf configs/config.yaml")
}

func newApp(logger log.Logger, hs *http.Server, gs *grpc.Server) *kratos.App {
	return kratos.New(
		kratos.ID(id),
		kratos.Name(Name),
		kratos.Version(Version),
		kratos.Metadata(map[string]string{}),
		kratos.Logger(logger),
		kratos.Server(
			hs,
			gs,
		),
	)
}

func main() {
	flag.Parse()
	c := config.New(
		config.WithSource(
			file.NewSource(flagconf),
		),
	)
	defer c.Close()

	if err := c.Load(); err != nil {
		panic(err)
	}

	var bc conf.Bootstrap
	if err := c.Scan(&bc); err != nil {
		panic(err)
	}

	lg, closeLog, err := logger.NewLoggerFromProtoConfig(bc.Logger, logger.Meta{
		ID: id, Name: Name, Version: Version,
	})
	if err != nil {
		panic(err)
	}
	defer closeLog()

	httpAddr, grpcAddr := "0.0.0.0:8000", "0.0.0.0:9000"
	if bc.Server != nil {
		if h := bc.Server.GetHttp(); h != nil && h.GetAddr() != "" {
			httpAddr = h.GetAddr()
		}
		if g := bc.Server.GetGrpc(); g != nil && g.GetAddr() != "" {
			grpcAddr = g.GetAddr()
		}
	}
	apilist.PrintSupportedAPIs(httpAddr, grpcAddr)

	app, cleanup, err := wireApp(bc.Server, bc.Data, bc.Jwt, bc.Sms, bc.AiAgent, bc.Wechat, lg)
	if err != nil {
		panic(err)
	}
	defer cleanup()

	// start and wait for stop signal
	if err := app.Run(); err != nil {
		panic(err)
	}
}
