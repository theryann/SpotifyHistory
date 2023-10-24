-- Order matters!!

-- Deletes files on Laptop that got a path there
UPDATE Album SET imgBigLocal = NULL WHERE imgBigLocal LIKE 'images/%';
UPDATE Album SET imgSmallLocal = NULL WHERE imgSmallLocal LIKE 'images/%';
UPDATE Artist SET imgBigLocal = NULL WHERE imgBigLocal LIKE 'images/%';
UPDATE Artist SET imgSmallLocal = NULL WHERE imgSmallLocal LIKE 'images/%';

-- Adjusts the paths on Pi to be just local paths that still need a full reference
UPDATE Album SET imgBigLocal = SUBSTR(imgBigLocal, 29) WHERE imgBigLocal LIKE '/media/%';
UPDATE Album SET imgSmallLocal = SUBSTR(imgSmallLocal, 29) WHERE imgSmallLocal LIKE '/media/%';
UPDATE Artist SET imgBigLocal = SUBSTR(imgBigLocal, 29) WHERE imgBigLocal LIKE '/media/%';
UPDATE Artist SET imgSmallLocal = SUBSTR(imgSmallLocal, 29) WHERE imgSmallLocal LIKE '/media/%';

