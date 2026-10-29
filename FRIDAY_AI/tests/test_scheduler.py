import asyncio
from datetime import datetime,timedelta,timezone
import pytest
from backend import db
from backend.types import Schedule
from backend.safety import SafetyError
from automation import scheduler

def test_schedule_creation_requires_future_time():
    past=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
    with pytest.raises(SafetyError): scheduler.create(Schedule(kind='reminder',label='Test',when=past))
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    result=scheduler.create(Schedule(kind='reminder',label='Test',when=future,repeat='daily'))
    assert result.verified and db.schedules()[0]['repeat_mode']=='daily'

@pytest.mark.asyncio
async def test_due_reminder_logs_and_disables_once():
    due=(datetime.now(timezone.utc)-timedelta(seconds=2)).isoformat()
    db.save_schedule('reminder','Check the task',{},due,'once')
    stop=asyncio.Event();worker=asyncio.create_task(scheduler.run_loop(stop))
    await asyncio.sleep(.1);stop.set();await asyncio.wait_for(worker,2)
    assert db.actions()[0]['detail']=='Reminder: Check the task'
    assert db.schedules()[0]['enabled'] is False
