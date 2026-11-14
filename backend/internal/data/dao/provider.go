package dao

import "github.com/google/wire"

// ProviderSet is data providers.
var ProviderSet = wire.NewSet(
	NewData,
	NewDB,
	NewRedis,
	NewUserRepository,
	NewChildRepository,
	NewAssignmentRepository,
	NewStoryContentRepository,
	NewQuestionGenerationRepository,
	NewQuestionAnswerRepository,
	NewVoiceTaskRepository,
	NewVoiceCacheRepository,
)
