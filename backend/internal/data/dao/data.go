package dao

import (
	"context"
	"fmt"
	"time"

	"github.com/go-kratos/kratos/v2/log"
	"github.com/redis/go-redis/v9"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"homework_ai2easy/backend/internal/conf"
	"homework_ai2easy/backend/internal/data/model"
)

// Data 数据访问对象
type Data struct {
	db  *gorm.DB
	rdb *redis.Client
}

// NewData 创建数据访问对象
func NewData(db *gorm.DB, rdb *redis.Client) (*Data, func(), error) {
	cleanup := func() {
		log.NewHelper(log.DefaultLogger).Info("closing the data resources")
	}

	return &Data{
		db:  db,
		rdb: rdb,
	}, cleanup, nil
}

// NewDB 创建数据库连接
func NewDB(conf *conf.Data) (*gorm.DB, error) {
	db, err := gorm.Open(mysql.Open(conf.Database.Source), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	// 自动迁移
	if err := autoMigrate(db); err != nil {
		return nil, fmt.Errorf("failed to auto migrate: %w", err)
	}

	return db, nil
}

// NewRedis 创建 Redis 连接
func NewRedis(conf *conf.Data) (*redis.Client, error) {
	rdb := redis.NewClient(&redis.Options{
		Addr:     conf.Redis.Addr,
		Password: conf.Redis.Password,
		DB:       int(conf.Redis.Db),
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect redis: %w", err)
	}

	return rdb, nil
}

// autoMigrate 自动迁移数据库表
func autoMigrate(db *gorm.DB) error {
	return db.AutoMigrate(
		&model.User{},
		&model.Child{},
		&model.Assignment{},
		&model.StoryContent{},
		&model.QuestionGenerationStatus{},
		&model.QuestionAnswer{},
	)
}
