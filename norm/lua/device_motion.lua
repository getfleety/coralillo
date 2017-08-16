local lon            = ARGV[1]
local lat            = ARGV[2]
local device_uid     = ARGV[3]
local device_time    = ARGV[4]
local received_at    = ARGV[5]
local uuid_for_dev   = ARGV[6]
local uuid_for_fleet = ARGV[7]
local uuid_for_loc   = ARGV[8]
local outdated       = ARGV[9]

-- First find organization
local org_code    = device_uid:sub(1, 8)
local device_code = device_uid:sub(9, 13)

if org_code == '' or device_code == '' then
    return
end

-- Finds organization subdomain from its code
local function get_org_subdomain(org_code)
    local org_id = redis.call('HGET', 'organization:index_code', org_code)

    if org_id == false then
        return false
    end

    return redis.call('HGET', 'organization:'..org_id, 'subdomain')
end

-- Finds or creates the new devices fleet
local function get_or_create_fleet(org_subdomain)
    local fleet_index_key = org_subdomain..':fleet:index_abbr'
    local maybeid = redis.call('HGET', fleet_index_key, 'NDV')

    if maybeid == false then
        -- Create the new device fleet
        local new_dev_fleet_key = org_subdomain..':fleet:'..uuid_for_fleet

        redis.call('HSET', new_dev_fleet_key, 'abbr', 'NDV')
        redis.call('HSET', new_dev_fleet_key, 'name', 'Nuevos dispositivos')
        redis.call('HSET', org_subdomain..':fleet:index_abbr', 'NDV', uuid_for_fleet)

        return uuid_for_fleet
    end

    return maybeid
end

-- Finds or creates a device
local function get_or_create_dev(org_subdomain)
    local dev_index_code = org_subdomain..':device:index_code'
    local geo_key = org_subdomain..':device:geo_last_pos'

    -- Try to find this device in the database
    local prev_id = redis.call('HGET', dev_index_code, device_code)

    if prev_id == false then
        local dev_key = org_subdomain..':device:'..uuid_for_dev
        local fleet_id = nil

        -- create this device
        redis.call('HSET', dev_key, 'id', uuid_for_dev)
        redis.call('HSET', dev_key, 'code', device_code)
        redis.call('HSET', dev_key, 'created_at', received_at)
        redis.call('HSET', dev_key, 'last_pos_time', device_time)

        redis.call('HSET', dev_index_code, device_code, uuid_for_dev)

        -- add it to new vehicles fleet
        local fleet_id = get_or_create_fleet(org_subdomain)
        local fleet_rel_key = org_subdomain..':fleet:'..fleet_id..':srel_devices'

        -- relate each other
        redis.call('HSET', dev_key, 'fleet', fleet_id)
        redis.call('SADD', fleet_rel_key, uuid_for_dev)

        -- add the last position
        redis.call('GEOADD', geo_key, lon, lat, uuid_for_dev)

        return uuid_for_dev
    elseif outdated == '0' then
        local dev_key = org_subdomain..':device:'..prev_id

        redis.call('HSET', dev_key, 'last_pos_time', device_time)
        redis.call('GEOADD', geo_key, lon, lat, prev_id)
    end

    return prev_id
end

-- Creates the new entry in the location history
local function register_location(org_subdomain, dev_id)
    local loc_key = org_subdomain..':position:'..uuid_for_loc

    redis.call('HSET', loc_key, 'id', uuid_for_loc)
    redis.call('HSET', loc_key, 'lat', lat)
    redis.call('HSET', loc_key, 'lon', lon)
    redis.call('HSET', loc_key, 'time', device_time)
    redis.call('HSET', loc_key, 'rcvd', received_at)
    redis.call('HSET', loc_key, 'last_updated', device_time)

    local rel_key = org_subdomain..':device:'..dev_id..':zrel_location_history'

    -- relate this location to the device
    redis.call('ZADD', rel_key, device_time, uuid_for_loc)
end

-- Publishes a message in the appropiate channel
local function publish_new_position()
    local fleet_key = org_subdomain..':fleet:'..fleet_id

    redis.call('PUBLISH', fleet_key, cjson.encode({
        event = 'new-position',
        data = {
            id = loc_id,
            attributes = {
                lat          = tonumber(lat),
                lon          = tonumber(lon),
                time         = device_time,
                last_updated = device_time,
                rcvd         = received_at,
            },
            relations = {
                device = dev_id,
            },
        },
    }))
end

local function main()
    local org_subdomain = get_org_subdomain(org_code)

    if org_subdomain == false then
        return 1
    end

    local dev_id = get_or_create_dev(org_subdomain)

    register_location(org_subdomain, dev_id)

    return 0
end

return main()
