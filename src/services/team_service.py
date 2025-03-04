from typing import Dict, List, Optional
from datetime import datetime
import logging
from .stats_service import StatsService
from .image_service import ImageService
from ..config import settings
from collections import defaultdict

logger = logging.getLogger(__name__)

class TeamService:
    def __init__(self):
        self.stats_service = StatsService()
        self.image_service = ImageService()
        
    def get_team_of_day(self, date: datetime) -> Optional[Dict]:
        """Формирует команду дня"""
        daily_stats = self.stats_service.get_daily_stats(date)
        if not daily_stats:
            logger.error(f"Не удалось получить статистику за {date}")
            return None
            
        logger.info(f"Получена статистика за {date}. Количество игроков: {len(daily_stats['players'])}")
        
        # Группируем игроков по позициям
        players_by_position = self._group_players_by_position(daily_stats["players"])
        logger.info(f"Игроки сгруппированы по позициям: {', '.join(f'{pos}: {len(players)}' for pos, players in players_by_position.items())}")
        
        # Формируем команду согласно требуемому составу
        team = {
            "date": daily_stats["date"],
            "players": self._select_best_players(players_by_position),
            "total_points": 0
        }
        
        # Считаем общие очки команды
        team["total_points"] = sum(
            player["stats"]["total_points"] 
            for player in team["players"].values()
        )
        
        logger.info(f"Команда дня сформирована. Общие очки: {team['total_points']}")
        logger.info(f"Состав команды:")
        for pos, player in team["players"].items():
            logger.info(f"{pos}: {player['info']['name']} ({player['stats']['total_points']} очков)")
        
        return team
        
    def _group_players_by_position(self, players: List[Dict]) -> Dict[str, List[Dict]]:
        """Группирует игроков по позициям"""
        grouped_players = defaultdict(list)
        
        for player in players:
            position_id = player["info"]["primary_position"]
            if position_id in settings.PLAYER_POSITIONS:
                position = settings.PLAYER_POSITIONS[position_id]
                # Добавляем только игроков с положительными очками
                if player["stats"]["total_points"] > 0:
                    grouped_players[position].append(player)
                    logger.debug(f"Игрок {player['info']['name']} добавлен в группу {position} с {player['stats']['total_points']} очками")
        
        # Сортируем игроков по очкам в каждой позиции
        for position in grouped_players:
            grouped_players[position].sort(
                key=lambda x: x["stats"]["total_points"],
                reverse=True
            )
            if grouped_players[position]:
                logger.debug(f"Лучший игрок в позиции {position}: {grouped_players[position][0]['info']['name']} ({grouped_players[position][0]['stats']['total_points']} очков)")
        
        return dict(grouped_players)
        
    def _select_best_players(self, players_by_position: Dict) -> Dict:
        """Выбирает лучших игроков для команды дня"""
        selected = {}
        
        # Выбираем нужное количество игроков для каждой позиции
        for position, count in settings.TEAM_OF_DAY_COMPOSITION.items():
            players = players_by_position.get(position, [])
            # Выбираем лучших игроков для каждой позиции
            for i, player in enumerate(players[:count]):
                pos_key = position if count == 1 else f"{position}{i+1}"
                selected[pos_key] = player
                logger.info(f"Выбран игрок {player['info']['name']} ({pos_key}) с {player['stats']['total_points']} очками")
        
        return selected
        
    def create_team_collage(self, team: Dict) -> Optional[str]:
        """Создает коллаж команды"""
        # Получаем фото всех игроков
        player_photos = {}
        for player_id, player_data in team["players"].items():
            # Добавляем поле position на основе primary_position
            player_data["info"]["position"] = settings.PLAYER_POSITIONS[player_data["info"]["primary_position"]]
            photo = self.image_service.get_player_photo(
                player_id,
                player_data["info"]["name"]
            )
            if photo:
                player_photos[player_id] = photo
                
        if len(player_photos) != len(team["players"]):
            logger.warning("Не удалось получить фото всех игроков")
            
        # Создаем коллаж
        return self.image_service.create_collage(
            player_photos,
            team["players"],
            team["date"],
            team["total_points"]
        ) 