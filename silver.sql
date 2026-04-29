CREATE OR REPLACE PROCEDURE TEAM5PM_PRODUCT.SILVER.SP_BUILD_CANONICAL_PERFORMANCE()
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS '

BEGIN

    CREATE OR REPLACE TABLE SILVER.CANONICAL_PERFORMANCE AS

    -- =========================================
    -- YOUTUBE
    -- =========================================
    SELECT
        raw_response:id::STRING AS content_id,
        ''youtube'' AS platform,
        brand_id,

        raw_response:snippet:title::STRING AS content_title,
        raw_response:snippet:publishedAt::TIMESTAMP_NTZ AS published_at,

        (
            COALESCE(REGEXP_SUBSTR(raw_response:contentDetails:duration::STRING, ''(\\\\d+)H'', 1, 1, ''e'', 1)::INT, 0) * 3600 +
            COALESCE(REGEXP_SUBSTR(raw_response:contentDetails:duration::STRING, ''(\\\\d+)M'', 1, 1, ''e'', 1)::INT, 0) * 60 +
            COALESCE(REGEXP_SUBSTR(raw_response:contentDetails:duration::STRING, ''(\\\\d+)S'', 1, 1, ''e'', 1)::INT, 0)
        ) AS duration_seconds,

        ''video'' AS content_type,

        raw_response:statistics:viewCount::INT,
        raw_response:statistics:likeCount::INT,
        raw_response:statistics:commentCount::INT,
        0,
        0,

        raw_response:statistics:viewCount::INT,
        (raw_response:statistics:likeCount::INT +
         raw_response:statistics:commentCount::INT),

        NULL,
        NULL,

        LENGTH(raw_response:snippet:title::STRING),
        raw_response:snippet:title::STRING LIKE ''%#%'',
        REGEXP_COUNT(raw_response:snippet:title::STRING, ''#''),
        REGEXP_LIKE(raw_response:snippet:title::STRING, ''[😀-🙏]''),
        REGEXP_COUNT(raw_response:snippet:title::STRING, ''@''),

        FALSE,
        TRUE,

        CURRENT_TIMESTAMP(),
        ''v1''

    FROM BRONZE.RAW_SOCIAL_DATA
    WHERE platform = ''youtube''

    UNION ALL

    -- =========================================
    -- INSTAGRAM
    -- =========================================
    SELECT
        raw_response:id::STRING,
        ''instagram'',
        brand_id,

        raw_response:caption::STRING,
        raw_response:timestamp::TIMESTAMP_NTZ,

        NULL,
        raw_response:media_type::STRING,

        NULL,
        raw_response:like_count::INT,
        raw_response:comments_count::INT,
        0,
        0,

        raw_response:like_count::INT,
        (raw_response:like_count::INT + raw_response:comments_count::INT),

        NULL,
        NULL,

        LENGTH(raw_response:caption::STRING),
        raw_response:caption::STRING LIKE ''%#%'',
        REGEXP_COUNT(raw_response:caption::STRING, ''#''),
        REGEXP_LIKE(raw_response:caption::STRING, ''[😀-🙏]''),
        REGEXP_COUNT(raw_response:caption::STRING, ''@''),

        FALSE,
        TRUE,

        CURRENT_TIMESTAMP(),
        ''v1''

    FROM BRONZE.RAW_SOCIAL_DATA
    WHERE platform = ''instagram''

    UNION ALL

    -- =========================================
    -- FACEBOOK
    -- =========================================
    SELECT
        raw_response:id::STRING,
        ''facebook'',
        brand_id,

        raw_response:message::STRING,
        raw_response:created_time::TIMESTAMP_NTZ,

        NULL,
        ''post'',

        NULL,
        raw_response:likes:summary:total_count::INT,
        raw_response:comments:summary:total_count::INT,
        raw_response:shares:count::INT,
        0,

        raw_response:likes:summary:total_count::INT,
        (
            raw_response:likes:summary:total_count::INT +
            raw_response:comments:summary:total_count::INT +
            raw_response:shares:count::INT
        ),

        NULL,
        NULL,

        LENGTH(raw_response:message::STRING),
        raw_response:message::STRING LIKE ''%#%'',
        REGEXP_COUNT(raw_response:message::STRING, ''#''),
        REGEXP_LIKE(raw_response:message::STRING, ''[😀-🙏]''),
        REGEXP_COUNT(raw_response:message::STRING, ''@''),

        FALSE,
        TRUE,

        CURRENT_TIMESTAMP(),
        ''v1''

    FROM BRONZE.RAW_SOCIAL_DATA
    WHERE platform = ''facebook''

    UNION ALL

    -- =========================================
    -- TIKTOK
    -- =========================================
    SELECT
        raw_response:id::STRING,
        ''tiktok'',
        brand_id,

        raw_response:desc::STRING,
        NULL,

        NULL,
        ''video'',

        raw_response:stats:playCount::INT,
        raw_response:stats:diggCount::INT,
        raw_response:stats:commentCount::INT,
        raw_response:stats:shareCount::INT,
        0,

        raw_response:stats:playCount::INT,
        (
            raw_response:stats:diggCount::INT +
            raw_response:stats:commentCount::INT +
            raw_response:stats:shareCount::INT
        ),

        NULL,
        NULL,

        LENGTH(raw_response:desc::STRING),
        raw_response:desc::STRING LIKE ''%#%'',
        REGEXP_COUNT(raw_response:desc::STRING, ''#''),
        REGEXP_LIKE(raw_response:desc::STRING, ''[😀-🙏]''),
        REGEXP_COUNT(raw_response:desc::STRING, ''@''),

        FALSE,
        TRUE,

        CURRENT_TIMESTAMP(),
        ''v1''

    FROM BRONZE.RAW_SOCIAL_DATA
    WHERE platform = ''tiktok'';

    RETURN ''SUCCESS: SILVER TABLE REBUILT'';

END;

';