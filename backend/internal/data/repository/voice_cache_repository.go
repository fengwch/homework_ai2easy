package repository

import "context"

// VoiceCacheRepository 朗读内容缓存仓储：相同 text+voice+format 命中缓存时直接返回已合成音频，避免重复调用 TTS
type VoiceCacheRepository interface {
	// Get 根据缓存 key 获取已缓存的合成结果（仅 completed 状态会写入缓存）
	Get(ctx context.Context, cacheKey string) (*VoiceTaskState, bool, error)
	// Set 将合成结果写入缓存，供后续相同内容复用
	Set(ctx context.Context, cacheKey string, state *VoiceTaskState) error
}
