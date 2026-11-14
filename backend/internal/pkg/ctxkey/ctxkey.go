package ctxkey

import "context"

// 包级 key，保证 WithValue / Value 使用同一 identity，否则 ctx.Value 取不到。
var userIDKey struct{}

// WithUserID 将 user_id 存入 context。
func WithUserID(ctx context.Context, userID uint64) context.Context {
	return context.WithValue(ctx, userIDKey, userID)
}

// UserIDFromContext 从 context 读取 user_id；不存在或类型不对时 ok 为 false。
func UserIDFromContext(ctx context.Context) (userID uint64, ok bool) {
	v := ctx.Value(userIDKey)
	if v == nil {
		return 0, false
	}
	id, ok := v.(uint64)
	return id, ok
}
