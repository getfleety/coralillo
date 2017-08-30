local allow_key = KEYS[1]

local objspec = ARGV[1]
local restrict = nil

if ARGV[2] ~= 'None' then
    restrict = ARGV[2]
end

local function split(thing)
    local pieces = {}

    for piece in thing:gmatch('%w+') do
        pieces[#pieces+1] = piece
    end

    return pieces
end

local function join_n(pieces, n)
    local res = ''

    for i, piece in pairs(pieces) do
        res = res..piece

        if i ~= n then
            res = res..':'
        else
            break
        end
    end

    return res
end

local function has_higher_permission(objspec, restrict)
    local pieces = split(objspec)

    for i = #pieces,1,-1 do
        local node = join_n(pieces, i)

        if redis.call('SISMEMBER', allow_key, node) ~= 0 then
            return 1
        end

        if restrict and redis.call('SISMEMBER', allow_key, node..'/'..restrict) ~= 0 then
            return 1
        end
    end

    return 0
end

local function startswith(str, prefix)
    for i=1,math.min(str:len(), prefix:len()) do
        if str:sub(i, i) ~= prefix:sub(i, i) then
            return false
        end
    end

    return true
end

local function delete_lower_permissions(objspec)
    for i, perm in pairs(redis.call('SMEMBERS', allow_key)) do
        if startswith(perm, objspec) then
            redis.call('SREM', allow_key, perm)
        end
    end
end

local function main()
    if has_higher_permission(objspec, restrict) == 1 then
        return 0 -- already had permission for that, no permission added
    end

    delete_lower_permissions(objspec)

    if not restrict then
        redis.call('SADD', allow_key, objspec)
    else
        redis.call('SADD', allow_key, objspec..'/'..restrict)
    end

    return 1
end

return main()
