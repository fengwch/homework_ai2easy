package grpcService

import "github.com/google/wire"

// ProviderSet is service providers.
var ProviderSet = wire.NewSet(
	NewAuthService,
	NewChildService,
	NewUserService,
	NewAssignmentService,
	NewContentService,
	NewFileService,
)
