#!/bin/bash
# Скрипт для развертывания сервиса на удаленном сервере

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Функция для вывода сообщений
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Проверка аргументов
if [ "$#" -lt 1 ]; then
    echo "Использование: $0 <действие> [опции]"
    echo "Действия:"
    echo "  setup    - Первоначальная настройка сервера"
    echo "  deploy   - Развертывание/обновление сервиса"
    echo "  start    - Запуск сервиса"
    echo "  stop     - Остановка сервиса"
    echo "  restart  - Перезапуск сервиса"
    echo "  logs     - Просмотр логов"
    echo "  status   - Статус сервиса"
    echo "  backup   - Создание резервной копии"
    echo "  update   - Обновление кода и перезапуск"
    exit 1
fi

ACTION=$1
shift

# Конфигурация
DEPLOY_DIR="/opt/video-preview-service"
BACKUP_DIR="/var/backups/video-preview"
SERVICE_NAME="video-preview-api"

# Функция первоначальной настройки
setup_server() {
    log "Начинаем настройку сервера..."
    
    # Обновление системы
    log "Обновление пакетов..."
    sudo apt-get update
    sudo apt-get upgrade -y
    
    # Установка Docker
    if ! command -v docker &> /dev/null; then
        log "Установка Docker..."
        curl -fsSL https://get.docker.com | sudo sh
        sudo usermod -aG docker $USER
        sudo systemctl enable docker
        sudo systemctl start docker
    else
        log "Docker уже установлен"
    fi
    
    # Установка Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log "Установка Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    else
        log "Docker Compose уже установлен"
    fi
    
    # Создание директорий
    log "Создание директорий..."
    sudo mkdir -p $DEPLOY_DIR
    sudo mkdir -p $BACKUP_DIR
    sudo mkdir -p $DEPLOY_DIR/previews
    sudo mkdir -p $DEPLOY_DIR/logs
    
    # Установка прав
    sudo chown -R $USER:$USER $DEPLOY_DIR
    sudo chown -R $USER:$USER $BACKUP_DIR
    
    # Настройка firewall
    log "Настройка firewall..."
    sudo ufw allow 22/tcp
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow 8080/tcp
    sudo ufw --force enable
    
    log "Настройка сервера завершена!"
    warning "Не забудьте перелогиниться для применения прав Docker"
}

# Функция развертывания
deploy_service() {
    log "Развертывание сервиса..."
    
    # Проверка наличия файлов
    if [ ! -f "Dockerfile" ] || [ ! -f "docker-compose.yml" ]; then
        error "Отсутствуют необходимые файлы (Dockerfile, docker-compose.yml)"
    fi
    
    # Копирование файлов
    log "Копирование файлов..."
    cp -r ../* $DEPLOY_DIR/
    
    # Создание .env если не существует
    if [ ! -f "$DEPLOY_DIR/.env" ]; then
        log "Создание .env файла..."
        cp .env.example $DEPLOY_DIR/.env
        warning "Отредактируйте $DEPLOY_DIR/.env перед запуском!"
    fi
    
    # Сборка образа
    log "Сборка Docker образа..."
    cd $DEPLOY_DIR
    docker-compose build
    
    log "Развертывание завершено!"
}

# Управление сервисом
start_service() {
    log "Запуск сервиса..."
    cd $DEPLOY_DIR
    docker-compose up -d
    sleep 5
    docker-compose ps
}

stop_service() {
    log "Остановка сервиса..."
    cd $DEPLOY_DIR
    docker-compose down
}

restart_service() {
    log "Перезапуск сервиса..."
    stop_service
    start_service
}

# Просмотр логов
show_logs() {
    cd $DEPLOY_DIR
    docker-compose logs -f --tail=100
}

# Статус сервиса
show_status() {
    log "Статус сервиса:"
    cd $DEPLOY_DIR
    docker-compose ps
    echo ""
    log "Использование ресурсов:"
    docker stats --no-stream $SERVICE_NAME
    echo ""
    log "Проверка здоровья:"
    curl -s http://localhost:8080/health | jq . || echo "Сервис недоступен"
}

# Создание резервной копии
create_backup() {
    log "Создание резервной копии..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.tar.gz"
    
    # Архивирование
    cd $DEPLOY_DIR
    sudo tar -czf $BACKUP_FILE \
        .env \
        docker-compose.yml \
        previews/ \
        logs/ \
        2>/dev/null || true
    
    # Удаление старых бэкапов (оставляем последние 5)
    ls -t $BACKUP_DIR/backup_*.tar.gz | tail -n +6 | xargs -r rm
    
    log "Резервная копия создана: $BACKUP_FILE"
}

# Обновление сервиса
update_service() {
    log "Обновление сервиса..."
    
    # Создание бэкапа
    create_backup
    
    # Остановка сервиса
    stop_service
    
    # Обновление кода
    log "Обновление кода..."
    if [ -d "$DEPLOY_DIR/.git" ]; then
        cd $DEPLOY_DIR
        git pull
    else
        warning "Git репозиторий не найден, обновите файлы вручную"
    fi
    
    # Пересборка и запуск
    deploy_service
    start_service
    
    log "Обновление завершено!"
}

# Выполнение действия
case $ACTION in
    setup)
        setup_server
        ;;
    deploy)
        deploy_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    backup)
        create_backup
        ;;
    update)
        update_service
        ;;
    *)
        error "Неизвестное действие: $ACTION"
        ;;
esac