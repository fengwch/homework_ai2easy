package dao

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"homework_ai2easy/backend/internal/data/repository"
)

const voiceTaskKeyPrefix = "voice:task:"
const voiceTaskTTL = time.Hour

var _ repository.VoiceTaskRepository = (*voiceTaskDao)(nil)

type voiceTaskDao struct {
	data *Data
}

// NewVoiceTaskRepository 创建语音任务仓储（Redis）
func NewVoiceTaskRepository(data *Data) repository.VoiceTaskRepository {
	return &voiceTaskDao{data: data}
}

func (d *voiceTaskDao) SetTask(ctx context.Context, taskID string, state *repository.VoiceTaskState) error {
	if taskID == "" || state == nil {
		return fmt.Errorf("task_id and state required")
	}
	key := voiceTaskKeyPrefix + taskID
	raw, err := json.Marshal(state)
	if err != nil {
		return err
	}
	return d.data.rdb.Set(ctx, key, raw, voiceTaskTTL).Err()
}

func (d *voiceTaskDao) GetTask(ctx context.Context, taskID string) (*repository.VoiceTaskState, bool, error) {
	if taskID == "" {
		return nil, false, nil
	}
	key := voiceTaskKeyPrefix + taskID
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
