package dao

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"homework_ai2easy/backend/internal/data/repository"
)

const voiceCacheKeyPrefix = "voice:cache:"
const voiceCacheTTL = 24 * time.Hour // 朗读内容缓存 24 小时

var _ repository.VoiceCacheRepository = (*voiceCacheDao)(nil)

type voiceCacheDao struct {
	data *Data
}

// NewVoiceCacheRepository 创建朗读内容缓存仓储（Redis）
func NewVoiceCacheRepository(data *Data) repository.VoiceCacheRepository {
	return &voiceCacheDao{data: data}
}

func (d *voiceCacheDao) Get(ctx context.Context, cacheKey string) (*repository.VoiceTaskState, bool, error) {
	if cacheKey == "" {
		return nil, false, nil
	}
	key := voiceCacheKeyPrefix + cacheKey
	raw, err := d.data.rdb.Get(ctx, key).Bytes()
	if err != nil {
		if err == redis.Nil {
			return nil, false, nil
		}
		return nil, false, err
	}
	var state repository.VoiceTaskState
	if err := json.Unmarshal(raw, &state); err != nil {
		return nil, false, err
	}
	return &state, true, nil
}

func (d *voiceCacheDao) Set(ctx context.Context, cacheKey string, state *repository.VoiceTaskState) error {
	if cacheKey == "" || state == nil {
		return fmt.Errorf("cache_key and state required")
	}
	key := voiceCacheKeyPrefix + cacheKey
	raw, err := json.Marshal(state)
	if err != nil {
		return err
	}
	return d.data.rdb.Set(ctx, key, raw, voiceCacheTTL).Err()
}
