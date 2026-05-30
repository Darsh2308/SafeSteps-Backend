from app.models.session import EmergencySession, SessionReport, TimelineEvent
from app.services.ai_service import ai_service
from app.utils.logger import Logger


class ReportService:
    async def generate_and_save_report(self, session: EmergencySession) -> SessionReport:
        Logger.info(f"Report: generating for session {session.id}")

        transcript_texts = [f"{t.speaker}: {t.text}" for t in session.transcripts]
        event_texts = [
            f"{e.timestamp.isoformat()} — {e.event}" for e in session.timeline
        ]
        threat_level = "LOW"
        if session.threat_assessments:
            threat_level = session.threat_assessments[-1].threat_level

        report_data = await ai_service.generate_report(
            session_id=session.id,
            transcripts=transcript_texts,
            events=event_texts,
            threat_level=threat_level,
        )

        report = SessionReport(
            threat_level=report_data.get("threatLevel", threat_level),
            incident_type=report_data.get("incidentType", "SOS Incident"),
            summary=report_data.get("summary", ""),
            actions_taken=report_data.get("actionsTaken", []),
            recommendations=report_data.get("recommendations", []),
        )
        session.report = report
        session.timeline.append(TimelineEvent(event="Incident Report Generated"))
        return report


report_service = ReportService()
