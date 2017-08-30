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

return has_higher_permission(objspec, restrict)
