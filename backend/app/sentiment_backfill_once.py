"""One-time, user-authorized AI sentiment backfill for existing BAWASLU campaign posts.

Activation requires two administrator-controlled environment variables, with a
specific frozen campaign/result-ID ceiling. No future posts are included.
No source text or provider credential is logged.
"""
import logging
import os
import time
from sqlalchemy import text

LOG=logging.getLogger(__name__)
RUN_ID='BAWASLU-SENTIMENT-20261030'
CAMPAIGN_ID=1
SOURCE_ID_CEILING=463
MAX_PROVIDER_REQUESTS=350
LOCK_KEY=10930463

def enabled():
    return (os.getenv('BAWASLU_SENTIMENT_BACKFILL_ENABLED','false').lower()=='true'
            and os.getenv('BAWASLU_SENTIMENT_BACKFILL_RUN_ID','')==RUN_ID)

def run_once():
    """Reuses the authorized post sentiment processor; never touches relevance."""
    if not enabled():
        return {'status':'DISABLED'}
    from .db import SessionLocal, engine
    from .models import CampaignEvidence, SocialListeningResult
    from .sentiment_processing import sentiment_is_assessed
    from .campaigns import _current_assessment,_classify_campaign_sentiment
    from .openai_triage import openai_triage_configured
    if not openai_triage_configured():
        LOG.error('SENTIMENT_BACKFILL blocked: OpenAI provider is not configured')
        return {'status':'BLOCKED_PROVIDER_NOT_CONFIGURED'}
    # This is a service actor, not an impersonated human decision-maker.
    principal={'id':'service:sentiment-backfill-20261030',
               'name':'Authorized automated sentiment backfill (2026-10-30)',
               'status':'Active','role':'National Administrator',
               'geographic_scope':'Nationwide',
               'permissions':{'administration':True,'view_intelligence':True}}
    # Session-level advisory lock avoids double billing across Render instances.
    with engine.connect() as lock:
        if lock.dialect.name=='postgresql':
            acquired=bool(lock.execute(text('SELECT pg_try_advisory_lock(:key)'),
                                        {'key':LOCK_KEY}).scalar())
            lock.commit()
            if not acquired:
                LOG.warning('SENTIMENT_BACKFILL already running on another instance')
                return {'status':'ALREADY_RUNNING'}
        try:
            db=SessionLocal()
            try:
                from .models import MonitoringCampaign
                campaign=db.get(MonitoringCampaign,CAMPAIGN_ID)
                if campaign is None:
                    LOG.error('SENTIMENT_BACKFILL campaign missing')
                    return {'status':'BLOCKED_CAMPAIGN_MISSING'}
                source_ids=[row[0] for row in db.query(CampaignEvidence.result_id).
                    join(SocialListeningResult,SocialListeningResult.id==CampaignEvidence.result_id).
                    filter(CampaignEvidence.campaign_id==CAMPAIGN_ID,
                           CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',
                           CampaignEvidence.result_id<=SOURCE_ID_CEILING,
                           SocialListeningResult.text_content.isnot(None),
                           SocialListeningResult.text_content!='').
                    order_by(CampaignEvidence.result_id).all()]
            finally:
                db.close()
            done=0;cached=0;attempted=0
            LOG.warning('SENTIMENT_BACKFILL started run=%s campaign=%s snapshot=%s max_paid=%s',
                        RUN_ID,CAMPAIGN_ID,len(source_ids),MAX_PROVIDER_REQUESTS)
            for rid in source_ids:
                db=SessionLocal()
                try:
                    campaign=db.get(MonitoringCampaign,CAMPAIGN_ID)
                    if sentiment_is_assessed(_current_assessment(db,CAMPAIGN_ID,rid)):
                        cached+=1
                        continue
                    if attempted>=MAX_PROVIDER_REQUESTS:
                        LOG.error('SENTIMENT_BACKFILL stopped: maximum paid requests reached')
                        return {'status':'STOPPED_MAX_REQUESTS','new':done,'cached':cached}
                    attempted+=1
                    result=_classify_campaign_sentiment(
                        db,principal,campaign,{'result_id':str(rid),'confirm_ai_cost':True})
                    if result.get('paid_provider_called'):
                        done+=1
                    else:
                        cached+=1
                    if done%10==0 and done:
                        LOG.warning('SENTIMENT_BACKFILL progress new=%d skipped=%d total=%d',
                                    done,cached,len(source_ids))
                except Exception as exc:
                    db.rollback()
                    LOG.error('SENTIMENT_BACKFILL stopped at source_id=%d after %d new posts: %s',
                              rid,done,type(exc).__name__)
                    return {'status':'STOPPED_ERROR','source_id':rid,'new':done,'cached':cached}
                finally:
                    db.close()
                time.sleep(0.25)
            LOG.warning('SENTIMENT_BACKFILL completed run=%s new=%d cached=%d total=%d',
                        RUN_ID,done,cached,len(source_ids))
            return {'status':'COMPLETED','new':done,'cached':cached,'total':len(source_ids)}
        finally:
            if lock.dialect.name=='postgresql':
                lock.execute(text('SELECT pg_advisory_unlock(:key)'),{'key':LOCK_KEY})
                lock.commit()
