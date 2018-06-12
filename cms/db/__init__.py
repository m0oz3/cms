#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2010-2012 Giovanni Mascellani <mascellani@poisson.phc.unipi.it>
# Copyright © 2010-2017 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2010-2012 Matteo Boscariol <boscarim@hotmail.com>
# Copyright © 2013 Bernard Blackham <bernard@largestprime.net>
# Copyright © 2013-2018 Luca Wehrstedt <luca.wehrstedt@gmail.com>
# Copyright © 2016 Myungwoo Chun <mc.tamaki@gmail.com>
# Copyright © 2016 Masaki Hara <ackie.h.gmai@gmail.com>
# Copyright © 2016 Amir Keivan Mohtashami <akmohtashami97@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Utilities functions that interacts with the database.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins.disabled import *  # noqa
from future.builtins import *  # noqa

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import configure_mappers, joinedload, subqueryload

from cms import config


logger = logging.getLogger(__name__)


# Define what this package will provide.

__all__ = [
    "version", "engine",
    # session
    "Session", "ScopedSession", "SessionGen", "custom_psycopg2_connection",
    # types
    "CastingArray",
    # base
    "metadata", "Base",
    # fsobject
    "FSObject", "LargeObject",
    # validation
    "CodenameConstraint", "FilenameConstraint", "DigestConstraint",
    # contest
    "Contest", "Announcement",
    # user
    "User", "Team", "Participation", "Message", "Question",
    # admin
    "Admin",
    # task
    "Task", "Statement", "Attachment", "Dataset", "Manager", "Testcase",
    # submission
    "Submission", "File", "Token", "SubmissionResult", "Executable",
    "Evaluation",
    # usertest
    "UserTest", "UserTestFile", "UserTestManager", "UserTestResult",
    "UserTestExecutable",
    # printjob
    "PrintJob",
    # init
    "init_db",
    # drop
    "drop_db",
    # util
    "test_db_connection", "get_contest_list", "is_contest_id",
    "ask_for_contest", "get_submissions", "get_submission_results",
    "get_datasets_to_judge", "enumerate_files"
]


# Instantiate or import these objects.

version = 35

engine = create_engine(config.database, echo=config.database_debug,
                       pool_timeout=60, pool_recycle=120)


from .session import Session, ScopedSession, SessionGen, \
    custom_psycopg2_connection

from .types import CastingArray
from .base import metadata, Base
from .fsobject import FSObject, LargeObject
from .validation import CodenameConstraint, FilenameConstraint, \
    DigestConstraint
from .contest import Contest, Announcement
from .user import User, Team, Participation, Message, Question
from .admin import Admin
from .task import Task, Statement, Attachment, Dataset, Manager, Testcase
from .submission import Submission, File, Token, SubmissionResult, \
    Executable, Evaluation
from .usertest import UserTest, UserTestFile, UserTestManager, \
    UserTestResult, UserTestExecutable
from .printjob import PrintJob

from .init import init_db
from .drop import drop_db

from .util import test_db_connection, get_contest_list, is_contest_id, \
    ask_for_contest, get_submissions, get_submission_results, \
    get_datasets_to_judge, enumerate_files


configure_mappers()


# The following are methods of Contest that cannot be put in the right
# file because of circular dependencies.

def get_submissions_for_contest(self):
    """Return a list of submissions (with the information about the
    corresponding task) referring to the contest.

    returns (list): list of submissions.

    """
    return self.sa_session.query(Submission)\
               .join(Task).filter(Task.contest == self)\
               .options(joinedload(Submission.token))\
               .options(joinedload(Submission.results)).all()


def get_submission_results_for_contest(self):
    """Return a list of submission results for all submissions in
    the current contest, as evaluated against the active dataset
    for each task.

    returns ([SubmissionResult]): list of submission results.

    """
    return self.sa_session.query(SubmissionResult)\
               .join(Submission).join(Task).filter(Task.contest == self)\
               .filter(Task.active_dataset_id == SubmissionResult.dataset_id)\
               .all()


def get_user_tests_for_contest(self):
    """Return a list of user tests (with the information about the
    corresponding user) referring to the contest.

    return (list): list of user tests.

    """
    return self.sa_session.query(UserTest)\
               .join(Task).filter(Task.contest == self)\
               .options(joinedload(UserTest.results)).all()


def get_user_test_results_for_contest(self):
    """Returns a list of user_test results for all user_tests in
    the current contest, as evaluated against the active dataset
    for each task.

    returns (list): list of user test results.

    """
    return self.sa_session.query(UserTestResult)\
               .join(UserTest).join(Task).filter(Task.contest == self)\
               .filter(Task.active_dataset_id == UserTestResult.dataset_id)\
               .all()


def get_print_jobs_for_contest(self):
    """Return a list of print jobs of the contest.

    return ([PrintJob]): list of print jobs.

    """
    return self.sa_session.query(PrintJob)\
               .join(Participation).filter(Participation.contest == self)\
               .all()


Contest.get_submissions = get_submissions_for_contest
Contest.get_submission_results = get_submission_results_for_contest
Contest.get_user_tests = get_user_tests_for_contest
Contest.get_user_test_results = get_user_test_results_for_contest
Contest.get_print_jobs = get_print_jobs_for_contest


# The following is a method of Dataset that cannot be put in the right
# file because of circular dependencies.

def get_submission_results_for_dataset(self, dataset):
    """Return a list of all submission results against the specified
    dataset.

    Also preloads the executable and evaluation objects relative to
    the submission results.

    returns ([SubmissionResult]): list of submission results.

    """
    # We issue this query manually to optimize it: we load all
    # executables and evaluations at once instead of having SA
    # lazy-load them when we access them for each SubmissionResult,
    # one at a time.
    return self.sa_session\
        .query(SubmissionResult)\
        .filter(SubmissionResult.dataset == dataset)\
        .options(joinedload(SubmissionResult.submission))\
        .options(subqueryload(SubmissionResult.executables))\
        .options(subqueryload(SubmissionResult.evaluations))\
        .all()

Dataset.get_submission_results = get_submission_results_for_dataset
