-- Update the Silver Layer transformation to handle Apify TikTok schema
CREATE OR REPLACE PROCEDURE TEAM5PM_PRODUCT.SILVER.SP_BUILD_CANONICAL_PERFORMANCE()
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
BEGIN
    -- 1. Ensure target table exists with the full schema
    CREATE TABLE IF NOT EXISTS SILVER.CANONICAL_PERFORMANCE (
        content_id STRING,
        platform STRING,
        client_id STRING,
        brand_id STRING,
        content_title STRING,
        published_at TIMESTAMP_NTZ,
        duration_seconds INT,
        content_type STRING,
        raw_views INT,
        raw_likes INT,
        raw_comments INT,
        raw_shares INT,
        raw_saves INT,
        total_reach INT,
        total_engagement INT,
        engagement_rate_pct FLOAT,
        sentiment_score FLOAT,
        title_length INT,
        has_hashtags BOOLEAN,
        hashtag_count INT,
        has_emojis BOOLEAN,
        mention_count INT,
        is_weekend BOOLEAN,
        is_active BOOLEAN,
        processed_at TIMESTAMP_NTZ,
        version STRING
    );

    -- 2. Perform Incremental Merge
    MERGE INTO SILVER.CANONICAL_PERFORMANCE AS target
    USING (
        WITH deduplicated_bronze AS (
            SELECT *
            FROM BRONZE.RAW_SOCIAL_DATA
            -- Ensure we partition by client and brand to prevent cross-tenant deduplication
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY platform, platform_id, client_id, brand_id 
                ORDER BY ingested_at DESC
            ) = 1
        )
        SELECT * FROM (
            -- YOUTUBE
            SELECT
                platform_id AS content_id,
                'youtube' AS platform,
                client_id, brand_id,
                raw_response:snippet.title::STRING AS content_title,
                raw_response:snippet.publishedAt::TIMESTAMP_NTZ AS published_at,
                (
                    COALESCE(REGEXP_SUBSTR(raw_response:contentDetails.duration::STRING, '(\\d+)H', 1, 1, 'e', 1)::INT, 0) * 3600 +
                    COALESCE(REGEXP_SUBSTR(raw_response:contentDetails.duration::STRING, '(\\d+)M', 1, 1, 'e', 1)::INT, 0) * 60 +
                    COALESCE(REGEXP_SUBSTR(raw_response:contentDetails.duration::STRING, '(\\d+)S', 1, 1, 'e', 1)::INT, 0)
                ) AS duration_seconds,
                'video' AS content_type,
                raw_response:statistics.viewCount::INT AS raw_views,
                raw_response:statistics.likeCount::INT AS raw_likes,
                raw_response:statistics.commentCount::INT AS raw_comments,
                0 AS raw_shares, 0 AS raw_saves,
                raw_response:statistics.viewCount::INT AS total_reach,
                (raw_response:statistics.likeCount::INT + raw_response:statistics.commentCount::INT) AS total_engagement,
                CASE WHEN raw_response:statistics.viewCount::INT > 0 
                     THEN ((raw_response:statistics.likeCount::INT + raw_response:statistics.commentCount::INT) / raw_response:statistics.viewCount::INT) * 100
                     ELSE 0 END AS engagement_rate_pct,
                NULL AS sentiment_score,
                LENGTH(raw_response:snippet.title::STRING) AS title_length,
                raw_response:snippet.title::STRING LIKE '%#%' AS has_hashtags,
                REGEXP_COUNT(raw_response:snippet.title::STRING, '#') AS hashtag_count,
                REGEXP_LIKE(raw_response:snippet.title::STRING, '[😀-🙏]') AS has_emojis,
                REGEXP_COUNT(raw_response:snippet.title::STRING, '@') AS mention_count,
                (EXTRACT(DOW FROM raw_response:snippet.publishedAt::TIMESTAMP_NTZ) IN (0, 6)) AS is_weekend,
                TRUE AS is_active, CURRENT_TIMESTAMP() AS processed_at, 'v1' AS version
            FROM deduplicated_bronze WHERE platform = 'youtube'

            UNION ALL

            -- INSTAGRAM
            SELECT
                platform_id, 'instagram', client_id, brand_id,
                raw_response:caption::STRING, raw_response:timestamp::TIMESTAMP_NTZ,
                NULL, raw_response:media_type::STRING,
                NULL, raw_response:like_count::INT, raw_response:comments_count::INT, 0, 0,
                raw_response:like_count::INT, (raw_response:like_count::INT + raw_response:comments_count::INT),
                CASE WHEN raw_response:like_count::INT > 0 
                     THEN ((raw_response:like_count::INT + raw_response:comments_count::INT) / raw_response:like_count::INT) * 100
                     ELSE 0 END,
                NULL, LENGTH(raw_response:caption::STRING), raw_response:caption::STRING LIKE '%#%',
                REGEXP_COUNT(raw_response:caption::STRING, '#'), REGEXP_LIKE(raw_response:caption::STRING, '[😀-🙏]'),
                REGEXP_COUNT(raw_response:caption::STRING, '@'),
                (EXTRACT(DOW FROM raw_response:timestamp::TIMESTAMP_NTZ) IN (0, 6)),
                TRUE, CURRENT_TIMESTAMP(), 'v1'
            FROM deduplicated_bronze WHERE platform = 'instagram'

            UNION ALL

            -- FACEBOOK
            SELECT
                platform_id AS content_id,
                'facebook' AS platform,
                client_id, brand_id,
                COALESCE(raw_response:text::STRING, raw_response:message::STRING) AS content_title,
                COALESCE(raw_response:time::TIMESTAMP_NTZ, raw_response:created_time::TIMESTAMP_NTZ) AS published_at,
                CASE 
                    WHEN raw_response:isVideo::BOOLEAN = TRUE THEN (raw_response:media[0].playable_duration_in_ms::INT / 1000)
                    WHEN raw_response:is_video::BOOLEAN = TRUE THEN raw_response:length::INT
                    ELSE NULL 
                END AS duration_seconds,
                CASE WHEN COALESCE(raw_response:isVideo::BOOLEAN, raw_response:is_video::BOOLEAN) = TRUE THEN 'video' ELSE 'post' END AS content_type,
                COALESCE(raw_response:viewsCount::INT, raw_response:video_views::INT, 0) AS raw_views,
                COALESCE(raw_response:likes::INT, raw_response:reactionCount::INT, raw_response:like_count::INT, 0) AS raw_likes,
                COALESCE(raw_response:comments::INT, raw_response:commentCount::INT, raw_response:comments_count::INT, 0) AS raw_comments,
                COALESCE(raw_response:shares::INT, raw_response:share_count::INT, 0) AS raw_shares,
                0 AS raw_saves,
                COALESCE(raw_response:viewsCount::INT, raw_response:video_views::INT, raw_response:likes::INT, 0) AS total_reach,
                (COALESCE(raw_likes, 0) + COALESCE(raw_comments, 0) + COALESCE(raw_shares, 0)) AS total_engagement,
                CASE 
                    WHEN COALESCE(total_reach, 0) > 0 THEN (total_engagement / total_reach) * 100 
                    ELSE 0 
                END AS engagement_rate_pct,
                NULL AS sentiment_score,
                LENGTH(content_title) AS title_length,
                content_title LIKE '%#%' AS has_hashtags,
                REGEXP_COUNT(content_title, '#') AS hashtag_count,
                REGEXP_LIKE(content_title, '[^\\x00-\\x7F]') AS has_emojis,
                REGEXP_COUNT(content_title, '@') AS mention_count,
                (EXTRACT(DOW FROM published_at) IN (0, 6)) AS is_weekend,
                TRUE AS is_active, CURRENT_TIMESTAMP() AS processed_at, 'v2' AS version
            FROM deduplicated_bronze WHERE platform = 'facebook'

            UNION ALL

            -- TIKTOK (Optimized for Apify Scraper)
            SELECT
                platform_id AS content_id,
                'tiktok' AS platform,
                client_id, brand_id,
                raw_response:desc::STRING, 
                TO_TIMESTAMP_NTZ(raw_response:createTime::INT) AS published_at,
                COALESCE(raw_response:videoMeta.duration::INT, 0) AS duration_seconds,
                'video' AS content_type,
                raw_response:stats.playCount::INT AS raw_views,
                raw_response:stats.diggCount::INT AS raw_likes,
                raw_response:stats.commentCount::INT AS raw_comments,
                raw_response:stats.shareCount::INT AS raw_shares,
                0 AS raw_saves,
                raw_views AS total_reach,
                (COALESCE(raw_likes, 0) + COALESCE(raw_comments, 0) + COALESCE(raw_shares, 0)) AS total_engagement,
                CASE 
                    WHEN raw_views > 0 THEN (total_engagement / raw_views) * 100 
                    ELSE 0 
                END AS engagement_rate_pct,
                NULL AS sentiment_score,
                LENGTH(raw_response:desc::STRING) AS title_length,
                raw_response:desc::STRING LIKE '%#%' AS has_hashtags,
                REGEXP_COUNT(raw_response:desc::STRING, '#') AS hashtag_count,
                REGEXP_LIKE(raw_response:desc::STRING, '[^\\x00-\\x7F]') AS has_emojis,
                REGEXP_COUNT(raw_response:desc::STRING, '@') AS mention_count,
                (EXTRACT(DOW FROM published_at) IN (0, 6)) AS is_weekend,
                TRUE AS is_active, CURRENT_TIMESTAMP() AS processed_at, 'v2' AS version
            FROM deduplicated_bronze WHERE platform = 'tiktok'
        )
    ) AS source
    ON target.content_id = source.content_id AND target.platform = source.platform
    WHEN MATCHED THEN
        UPDATE SET
            target.raw_views = source.raw_views,
            target.raw_likes = source.raw_likes,
            target.raw_comments = source.raw_comments,
            target.raw_shares = source.raw_shares,
            target.total_reach = source.total_reach,
            target.total_engagement = source.total_engagement,
            target.engagement_rate_pct = source.engagement_rate_pct,
            target.processed_at = source.processed_at
    WHEN NOT MATCHED THEN
        INSERT (
            content_id, platform, client_id, brand_id, content_title, published_at, duration_seconds,
            content_type, raw_views, raw_likes, raw_comments, raw_shares, raw_saves, total_reach,
            total_engagement, engagement_rate_pct, sentiment_score, title_length, has_hashtags,
            hashtag_count, has_emojis, mention_count, is_weekend, is_active, processed_at, version
        ) VALUES (
            source.content_id, source.platform, source.client_id, source.brand_id, source.content_title,
            source.published_at, source.duration_seconds, source.content_type, source.raw_views,
            source.raw_likes, source.raw_comments, source.raw_shares, source.raw_saves, source.total_reach,
            source.total_engagement, source.engagement_rate_pct, source.sentiment_score, source.title_length,
            source.has_hashtags, source.hashtag_count, source.has_emojis, source.mention_count,
            source.is_weekend, source.is_active, source.processed_at, source.version
        );

    RETURN 'SUCCESS: SILVER TABLE INCREMENTALLY UPDATED';
END;
$$;