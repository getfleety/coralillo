local org = ARGV[1]
local query = ARGV[2]
local limit = 50

-- sort table by order function
local function spairs(t, order)
  -- collect the keys
  local keys = {}
  for k in pairs(t) do keys[#keys+1] = k end

  -- if order function given, sort by it by passing the table and keys a, b,
  -- otherwise just sort the keys 
  if order then
    table.sort(keys, function(a,b) return order(t, a, b) end)
  else
    table.sort(keys)
  end

  -- return the iterator function
  local i = 0
  return function()
    i = i + 1
    if keys[i] then
      return keys[i], t[keys[i]]
    end
  end
end

-- returns true if key is a redis object_key
local function is_object_key(key)
  local key_len = string.len(key)
  local next_index = nil

  local index = string.find(key, ':') + 1
  repeat
    next_index = string.find(key, ':', index)
    if next_index == nil then
      break
    end

    index = next_index + 1
  until true

  if (key_len - index + 1) ~= 32 then
    return false
  end

  local is_object_key = true
  for i=index, key_len do
    if string.find(key:sub(i,i), '[a-f0-9]') == nil then
      is_object_key = false
      break
    end
  end

  return is_object_key
end


-- levenshtein distance
local function string_distance(a, b)
  local a_len = a:len()
  local b_len = b:len()

  local lev = {}
  for i=0, a_len do
    lev[i] = {}

    for j=0, b_len do
      if i == 0 or j == 0 then
        lev[i][j] = math.max(i, j)
      else
        local d = lev[i-1][j] + 1

        d = math.min(lev[i-1][j] + 1, d)
        d = math.min(lev[i][j-1] + 1, d)

        if a:sub(i,i) == b:sub(j,j) then
          d = math.min(lev[i-1][j-1], d)
        else
          d = math.min(lev[i-1][j-1] + 1, d)
        end

        lev[i][j] = d
      end
    end
  end

  return lev[a_len][b_len]
end

-- Get org's devices params
local objects = {}
local devices = redis.call('keys', org .. ':device:*')
for index, key in pairs(devices) do
  if is_object_key(key) then
    local str = redis.call('hget', key, 'code')

    local name = redis.call('hget', key, 'name')
    if name then
      str = str .. ' ' .. name
    end

    local description = redis.call('hget', key, 'description')
    if description then
      str = str .. ' ' .. description
    end

    objects[key] = str
  end
end

-- Get org's geofences params
local geofences = redis.call('keys', org .. ':geofence:*')
for index, key in pairs(geofences) do
  if is_object_key(key) then
    objects[key] = redis.call('hget', key, 'name')
  end
end

-- Calc object's scores
local scores = {}
local min_score = 100000
local scores_len = 0
for key, value in pairs(objects) do
  local max_len = math.max(query:len(), value:len())
  local score = 100000 * (max_len - string_distance(query, value)) / max_len

  if score ~= 0 and (score >= min_score or scores_len < limit) then
    min_score = math.min(score, min_score)
    scores_len = scores_len + 1
    scores[key] = score
  end
end

-- Return first #limit answers
local answer = {}
for key, value in spairs(scores, function(t,a,b) return t[a] > t[b] end) do
  if #answer == limit then
    break
  end

  answer[#answer + 1] = key
end

return answer
