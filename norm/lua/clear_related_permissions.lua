-- Takes a fully qualified object id and clears every user's permissions
-- that have this id
local view_perm = ARGV[1]..':view'
local admin_perm = ARGV[1]

for i, user_id in pairs(redis.call('SMEMBERS', 'user:members')) do
    local allow_set_key = 'user:'..user_id..':allow'

    redis.call('SREM', allow_set_key, view_perm)
    redis.call('SREM', allow_set_key, admin_perm)
end
