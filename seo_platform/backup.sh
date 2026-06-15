#!/bin/bash
# تعریف مسیر ذخیره‌سازی بک‌آپ‌ها روی هاست ویندوز/لینوکس شما
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

# ایجاد فولدر بک‌آپ در صورت عدم وجود
mkdir -p $BACKUP_DIR

echo "Starting automated night database backup sequence..."

# فراخوانی ایمن کانتینر دیتابیس داکر بدون نیاز به پسورد متنی سخت‌افزاری
docker compose exec -t db pg_dumpall -c -U seo_admin > $BACKUP_FILE

if [ $? -eq 0 ]; then
    echo "Backup executed successfully! Saving to: $BACKUP_FILE"
    # نگهداری بک‌آپ‌های ۷ روز اخیر و حذف خودکار فایل‌های قدیمی‌تر جهت بهینه‌سازی دیسک
    find $BACKUP_DIR -type f -name "*.sql" -mtime +7 -exec rm {} \;
else
    echo "Database backup sequence crashed with errors."
    exit 1
fi