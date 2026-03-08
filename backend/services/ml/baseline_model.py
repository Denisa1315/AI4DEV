class BaselineModel:
    def update(self, user_id, physio_score, facial_score, voice_score, eli, hrv, hr):
        # In a real app, this would update the user's historical baseline in the DB
        pass

    def get_session_opening_context(self, user_id, current_eli, current_hrv, sleep_hours, day_of_week):
        return (
            f"Hello {user_id}. I notice your ELI is {current_eli} today. "
            f"Given you slept {sleep_hours} hours last night and your HRV is {current_hrv}, "
            f"let's focus on a relaxed session this {day_of_week}."
        )

baseline_model = BaselineModel()
