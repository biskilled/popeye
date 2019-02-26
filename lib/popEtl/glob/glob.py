# (c) 2017-2019, Tal Shany <tal.shany@biSkilled.com>
#
# This file is part of popEye
#
# popEye is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# popEye is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cadenceEtl.  If not, see <http://www.gnu.org/licenses/>.

import re
import sys
import os
import datetime
import logging
from collections import OrderedDict

from popEtl.glob.enums import eConnValues, eDbType, ePopEtlProp, isDbType
from  popEtl.config import config

def getLogger (
    LOG_FORMAT     = '%(asctime)s %(levelname)s %(message)s',
    LOG_DIR        = None,
    LOG_FILE       = 'file'
    ):

    #logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    logFormatter= logging.Formatter(LOG_FORMAT)
    logg  = logging.getLogger()

    if LOG_DIR:
        fileHandler = logging.FileHandler("{0}/{1}.log".format(LOG_DIR, LOG_FILE))
        fileHandler.setFormatter(logFormatter)
        logg.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    logg.addHandler(consoleHandler)

    logg.setLevel(logging.DEBUG)

    return logg


logg = getLogger ()
def p(msg, ind='I'):
    ind = ind.upper()
    indPrint = {'E': 'ERROR>> ',
                'I': 'Information>> ',
                'II': 'Info>> ',
                'III': 'Progress>> '}
    allowToPrint    = ['E', 'I','II', 'III']  #  'II', 'III'
    #allowToPrint = ['E','I']
    allowToSaveInDB_E = ['E']
    allowToSaveInDB_I = ['I']
    allowToSaveInDB = allowToSaveInDB_E + allowToSaveInDB_I

    if ind in allowToPrint or (config.LOGS_IN_DB and ind in allowToSaveInDB):
        localTime = datetime.datetime.today()
        if config.LOGS_IN_DB and ind in allowToSaveInDB_E:
            timeStr = localTime.strftime("%m/%d/%Y %H:%M:%S")
            config.LOGS_ARR_E.append((timeStr,config.LOGS_DB_TIME_STEMP, ind, str(msg)))
        elif config.LOGS_IN_DB and ind in allowToSaveInDB_I:
            timeStr = localTime.strftime("%m/%d/%Y %H:%M:%S")
            config.LOGS_ARR_I.append((timeStr,config.LOGS_DB_TIME_STEMP, ind, str(msg)))
        if config.LOGS_PRINT and ind in allowToPrint:
            timeStr = localTime.strftime("%d/%m/%Y %H:%M:%S")
            if 'III' in ind:
                logg.debug("\r %s %s" %(indPrint[ind], msg))
            elif 'II' in ind:
                logg.info("%s %s" %(indPrint[ind], msg))
            elif 'I' in ind:
                logg.warning("%s %s" %(indPrint[ind], msg))
            else:
                logg.error(str(indPrint[ind]) + str(msg))

def setQueryWithParams(query):
    qRet = ""
    if query and len (query)>0:
        if isinstance(query, (list,tuple)):
            for q in query:
                #q = str(q, 'utf-8')
                for param in config.QUERY_PARAMS:
                    if param in q:
                        q = q.replace(param, config.QUERY_PARAMS[param])
                        p("config->setQueryWithParams: replace param %s with value %s, sql: %s " % (str(param), str(config.QUERY_PARAMS[param]), str (q)), "ii")
                qRet += q
        else:
            #query= str (query, 'utf-8')

            for param in config.QUERY_PARAMS:
                if param in query:
                    query = query.replace(param, config.QUERY_PARAMS[param])
                    p("config->setQueryWithParams: replace param %s with value %s, sql: %s " % (str(param), str(config.QUERY_PARAMS[param]), str(query)), "ii")
            qRet += query
    else:
        qRet = query
    return qRet

def replaceStr (sString,findStr, repStr, ignoreCase=True):
    if ignoreCase:
        pattern = re.compile(re.escape(findStr), re.IGNORECASE)
        res = pattern.sub (repStr, sString)
    else:
        res = sString.replace (findStr, repStr)
    return bytes (res, 'utf8')

def decodeStrPython2Or3 (sObj, un=True):
    pVersion = sys.version_info[0]

    if 3 == pVersion:
        return sObj
    else:
        if un:
            return unicode (sObj)
        else:
            return str(sObj).decode("windows-1255")

def setDicConnValue (connJsonVal=None, connType=None, connName=None,
                     connObj=None, connFilter=None, connUrl=None, extraConnVal=None,
                     isSql=False, isTarget=False, isSource=False):
    retVal = {eConnValues.connName:connName,
              eConnValues.connType:connType.lower() if connType else None ,
              eConnValues.connUrl:connUrl,
              eConnValues.connUrlExParams:extraConnVal,
              eConnValues.connObj:connObj,
              eConnValues.connFilter:connFilter,
              eConnValues.connIsSql:isSql,
              eConnValues.connIsSrc:isSource,
              eConnValues.connIsTar:isTarget}

    if isinstance( connJsonVal, (tuple,list) ):
        if len (connJsonVal) == 1:
            retVal[eConnValues.connName] = connJsonVal[0]
        elif len (connJsonVal) >= 2:
            retVal[eConnValues.connName] = connJsonVal[0]
            retVal[eConnValues.connObj]  = connJsonVal[1]
            if retVal[eConnValues.connType] is None:
                retVal[eConnValues.connType] = connJsonVal[0].lower()
            if len (connJsonVal) == 3:
                retVal[eConnValues.connFilter]= connJsonVal[2]
        else:
            err = "glob->_setDicConnValue: Connection paramter is not valid %s must have 1,2 or 3 params: %s " %(str(connJsonVal))
            p(err, "e")
            raise Exception(err)

        if retVal[eConnValues.connName] is None:
            err = "glob->_setDicConnValue: Connection Name is not defined: %s " %(connJsonVal)
            p(err, "e")
            raise Exception(err)

        if retVal[eConnValues.connUrl] is None:
            if retVal[eConnValues.connName] in config.CONN_URL:
                connUrl = config.CONN_URL[ retVal[eConnValues.connName] ]
                retVal[eConnValues.connUrl] = connUrl
                if isinstance(connUrl, (dict, OrderedDict) ):
                    if eConnValues.connType in connUrl:
                        retVal[eConnValues.connType] = connUrl[eConnValues.connType].lower()
                    if eConnValues.connUrl in connUrl:
                        retVal[eConnValues.connUrl] = connUrl[eConnValues.connUrl]
            else:
                err = "glob->_setDicConnValue: Connection Name %s is not defined in CONN_URL config. define names are : %s  "  %(retVal[eConnValues.connName], str(list(config.CONN_URL.keys())))
                p(err, "e")
                raise Exception(err)
        # remove number from connection type in case we used it in config.CONN_URL
        # sample : sql1 - will be rename to sql as a type
        retVal[eConnValues.connType] = ''.join([i for i in retVal[eConnValues.connType].lower() if not i.isdigit()])

        # For access - add paramters
        if eDbType.ACCESS == retVal[eConnValues.connType] and retVal[eConnValues.connUrlExParams] is not None:
            retVal[eConnValues.connUrl] = retVal[eConnValues.connUrl][0] % (retVal[eConnValues.connUrl][1] + str(retVal[eConnValues.connUrlExParams].split(".")[0] + ".accdb"))

        retVal[eConnValues.connType] = isDbType( retVal[eConnValues.connType] )

        if  retVal[eConnValues.connName] is not None and \
            retVal[eConnValues.connType] is not None and \
            retVal[eConnValues.connObj] is not None and \
            retVal[eConnValues.connUrl] is not None:
                p ("glob->_setDicConnValue: Connection params: %s " %(str(retVal)),"ii")
                return retVal

        err = "glob->_setDicConnValue: Connection params are not set: %s " % (str(retVal))
        p(err, "e")
        raise Exception(err)

def getDicKey (etlProp, allProp):
    etlProp = str(etlProp).lower() if etlProp else ''
    if etlProp in ePopEtlProp.dicOfProp:
        etlProps = ePopEtlProp.dicOfProp[ etlProp ]

        filterSet = set (etlProps)
        allSet    = set ([str(x).lower() for x in allProp])
        isExists = filterSet.intersection(allSet)

        if len (isExists) > 0:
            return isExists.pop()
    return None

