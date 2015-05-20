# This file is part of Indico.
# Copyright (C) 2002 - 2015 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from datetime import timedelta

from celery.schedules import crontab

from indico.core.celery import celery
from indico.core.config import Config
from indico.core.db import DBMgr, db
from indico.modules.categories import logger
from indico.modules.users import User
from indico.util.date_time import now_utc
from MaKaC.conference import CategoryManager


@celery.periodic_task(name='category_cleanup', run_every=crontab(minute='0', hour='5'))
def category_cleanup():
    cfg = Config.getInstance()
    janitor_user = User.get_one(cfg.getJanitorUserId())

    logger.debug("Checking whether any categories should be cleaned up")
    for categ_id, days in cfg.getCategoryCleanup().iteritems():
        try:
            category = CategoryManager().getById(categ_id)
        except KeyError:
            logger.warning("Category {} does not exist!".format(categ_id))
            continue

        now = now_utc()
        to_delete = [ev for ev in category.conferences if (now - ev._creationDS) > timedelta(days=days)]
        if not to_delete:
            continue

        logger.info("Category {}: {} events were created more than {} days ago and will be deleted".format(
            categ_id, len(to_delete), days
        ))
        for i, event in enumerate(to_delete, 1):
            logger.info("Deleting {}".format(event))
            event.delete(user=janitor_user)
            if i % 100 == 0:
                db.session.commit()
                DBMgr.getInstance().commit()
        db.session.commit()
        DBMgr.getInstance().commit()
