#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 19:16:02 2018

@author: marian
"""
import os,sys,io
import random
import subprocess
import xml.etree.ElementTree 
import itertools
import pandas as pd
import re
import shutil
import math
import string
import copy


def silentremove(filename):
    try:
        os.remove(filename)
    except OSError as e: # this would be "except OSError, e:" before Python 2.6
        pass# re-raise except

class Apsimcrop:
    def __init__(self,cropfile):
        self.cropfile=cropfile
        self.cropxlm=xml.etree.ElementTree(cropfile)
        pass
    def change_par(self):
        pass

class Apsim:
    def __init__(self,simfile,apsimbin="ApsimModel.exe",isnewsim=False,isnewcrop=False):
        self.apsimfile=simfile
        self.apsimbin=apsimbin
        self.apsimxml=xml.etree.ElementTree.parse(simfile)
        self.must_run=True
        self.tempfiles=[]
        self.isnewsim=isnewsim
        self.isnewcrop=isnewcrop
        self.basedir=os.path.dirname(os.path.realpath(simfile))
        #atexit.register(self.destroy,drop_crops=True,drop_file=False,drop_output=True)
    
    def __enter__(self):
        return self
    
    def __del__(self):
        pass
        #self.destroy(drop_crops=self.isnewcrop,drop_file=self.isnewsim,drop_output=True)
        #print ("DELEEETEEE")

    def __exit__(self, exc_type, exc_value, traceback):
        self.destroy(drop_crops=self.isnewcrop,drop_file=self.isnewsim,drop_output=True)
                
    def unify_outfilenames(self):
        for sn in self.apsimxml.findall(".//simulation"):
            of_nodes=sn.findall(".//outputfile")
            for i in range(len(of_nodes)):
                #if (not "name" in of_nodes[i].attrib):
                of_nodes[i].attrib["name"]="ergebnisfile"+str(i+1)
                
    def parse_output(self):
        
        outfilelist=self.get_outfilenames()
        results={}
        
        for sublist in outfilelist:
            for ofname in sublist:
                lines=open(ofname).read().split("\n")
                if len(lines)<=2: continue
                del lines[0:2]
                del lines[1]
                rbuf=io.StringIO()
                rbuf.writelines("%s\n" % l for l in lines)
                rbuf.seek(0)
                results[ofname]=pd.read_csv(rbuf,"\s+")
        return(results)
        
                
    def get_outfilenames(self):
        result=[]
        default=True
        for sn in self.apsimxml.findall(".//simulation"):
            ofnames=[]
            ofnodes=sn.findall(".//outputfile")
            for i in range(len(ofnodes)):
                ofn=ofnodes[i]
                if "name" in ofn.attrib:
                    ofnames.append(sn.attrib["name"]+" "+ofn.attrib["name"]+".out")
                else:
                    if default:
                        ofnames.append(sn.attrib["name"]+".out")
                        default=False
                    else:
                        ofnames.append(sn.attrib["name"]+" "+"outputfile"+str(i)+".out")
                ofnames=[os.path.join(os.path.dirname(os.path.realpath(self.apsimfile)),f) for f in ofnames]
            result.append(ofnames)
        return(result)
                
    def destroy(self,drop_crops=False,drop_file=False,drop_output=True):
        if drop_file:
            #print ("deleteing "+self.apsimfile)
            silentremove(self.apsimfile)
        #os.unlink(self.apsimfile)
        if drop_crops:
            for cf in self.apsimxml.findall(".//ini/filename"):
                #print ("deleting "+cf.text)
                silentremove(os.path.join(self.basedir,cf.text))
        if drop_output:
            for ofn in list(itertools.chain(*self.get_outfilenames())):
                #print ("deleting "+ofn)
                silentremove(ofn)
        silentremove(self.apsimfile.replace(".apsim",".sim"))
        silentremove(self.apsimfile.replace(".apsim",".sims"))
        
    def set_simfile(self,simfile):
        self.apsimfile=simfile
        
    def run(self):
        #print("huhu")
        #cwd=os.getcwd()
        os.chdir(os.path.dirname(os.path.abspath(self.apsimfile)))
        
        cmd="nohup {} {} > /dev/null".format(self.apsimbin,os.path.basename(self.apsimfile))
        res=os.system(cmd)
        #out=os.popen(cmd)
        #p=subprocess.Popen(cmd.split(" "),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        
        
        #WINDOWS
        #p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        
        #(output, err) = p.communicate()
        #os.chdir(cwd)        
        #print (output)1!=0
        if res!=0:
            #if "Fatal" in err.decode("ascii")+output.decode("ascii"):
            #print("Error")
            #print(err.decode("ascii")+output.decode("ascii"))
            #print(os.getcwd)
            return([])
        else:
            #print("Success")
            output= self.parse_output()
            return (output)
        
    def set_weather(self,metfiles):
        metfilenodes=self.apsimxml.findall(".//metfile/filename")
        if type(metfiles)!="list": metfiles=[metfiles]
        for mfn,mf in zip(metfilenodes,itertools.cycle(metfiles)):
            mfn.text=mf
        self.apsimxml.write(self.apsimfile)
        pass
    
    def save(self,overwrite=True,newname=None):
        if (not overwrite):
            if newname is None:
                rndstr=''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                newfilename=re.sub("(.*)\.apsim$","\g<1>."+rndstr+".apsim",self.apsimfile)
            for sn in self.apsimxml.findall(".//simulation"):
                simname=sn.attrib["name"]
                if newname is None:
                    sn.attrib["name"]=simname+"_"+rndstr
                else:
                    sn.attrib["name"]=newname
        else:
            newfilename = self.apsimfile
            #print ("Writing apsim file"+newfilename)
            self.apsimxml.write(newfilename)
        return (self)
        #return (Apsim(newfilename,isnewsim=self.isnewsim,isnewcrop=self.isnewcrop))
        
    def set_sim_par(self,xpath,newtexts,overwrite=True,save=True):
        parnodes=self.apsimxml.findall(xpath)
        if type(newtexts)!="list": newtexts=[newtexts]
        for pn,nt in zip(parnodes,itertools.cycle(newtexts)):
            pn.text=nt
        if (save):
            return (self.save(overwrite=overwrite))
        else:
            return self
        pass
    
    
    def clone(self,clone_cropfiles=False,newname= None,save=True,namepostfix=None):
        newsim = copy.deepcopy(self)

        newsim.isnewsim=True
        newsim.isnewcrop=clone_cropfiles
        
        if namepostfix is None:
            namepostfix=''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        if newname is None:
            newname=re.sub("(.*)\.apsim$","\g<1>_"+namepostfix+".apsim",newsim.apsimfile)

        newsim.apsimfile=newname
        
        for sn in newsim.apsimxml.findall(".//simulation"):
            simname=sn.attrib["name"]
            #print ("Renaming"+simname)
            sn.attrib["name"]="_".join((simname,namepostfix))

        basedir=os.path.dirname(os.path.realpath(self.apsimfile))
        if clone_cropfiles:
            for cfn in newsim.apsimxml.findall(".//ini/filename"):
                oldcfname=cfn.text
                newcfname=re.sub("(.*)\.xml$","\g<1>."+namepostfix+".xml",oldcfname)
                shutil.copyfile(os.path.join(basedir,oldcfname),os.path.join(basedir,newcfname))
                cfn.text= newcfname
        
        if save:
            return (newsim.save(newname=newname,overwrite=True))
        else:
            return newsim

        #newsim=self.save(overwrite=F)
        pass
    
    def change_parseq(self,text,subelement=None):
        elements=text.split(" ")
        elements[subelement]=text
        return " ".join(elements)
    
    def get_crop_par(self,xpath,subelement):
        cropfilenodes=self.apsimxml.findall(".//ini/filename")
        parlist=[]
        for cfn in cropfilenodes:
            cf=xml.etree.ElementTree.parse(os.path.join(self.basedir,cfn.text))
            cropfileparnodes=cf.findall(xpath)
            for cfp in cropfileparnodes:
                elements=re.split("\s+",cfp.text.strip())
                if (math.isnan(subelement) or subelement=="all" or subelement is None):
                    parlist.append(elements)
                else:
                    parlist.append(elements[int(subelement)-1])
        return(parlist)
        
    def set_crop_pars(self,xpaths,newtexts,is_multiplier,subelements=None,overwrite_cropfile=True,overwrite_apsimfile=True):
        if not type(xpaths) is list: 
            xpaths=[xpaths]
        if not type(newtexts) is list:
            newtexts=[newtexts]
        if not type(subelements) is list:
            subelements=[subelements]
        if not type(is_multiplier) is list:
            is_multiplier=[is_multiplier]
        
        cropfilenodes=self.apsimxml.findall(".//ini/filename")
        
        for cfn in cropfilenodes:
            cf=xml.etree.ElementTree.parse(os.path.join(self.basedir,cfn.text))
            for xpath,newtext,subelement,multiply in zip(xpaths,newtexts,subelements,is_multiplier):
                cropfileparnodes=cf.findall(xpath)
                #print (str(len(cropfileparnodes))+"nodes found")
                for cfp in cropfileparnodes:
                    elements=re.split("\s+",cfp.text.strip())
                    if (subelement == "all" or math.isnan(subelement)):
                        if (multiply):
                            elements=[str(float(newtext)*float(e)) for e in elements]
                        else:
                            elements=[newtext for _ in elements]
                    else:
                        if (multiply):
                            elements[int(subelement)]=str(float(newtext)*float(elements[int(subelement)]))
                        else:
                            elements[int(subelement)]=newtext
                    #print ("Setting '{}[{}]' from '{}' to '{}'".format(xpath,subelement,cfp.text.strip(),elements) )
                    cfp.text=" ".join(elements)
            if (not overwrite_cropfile):
                rndstr=''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                newname=re.sub("(.*)\.xml$","\g<1>."+rndstr+".xml",cfn.text)
                self.set_sim_par(".//ini/filename",newname)
            else: 
                newname=cfn.text
            cf.write(os.path.join(self.basedir,newname))
        return (self.save(overwrite=overwrite_apsimfile))
        pass
    
    def set_crop_par(self,xpath,newtexts,subelement=None,overwrite_cropfile=True,overwrite_apsimfile=True):
        if type(newtexts)!="list": newtexts=[newtexts]
        cropfilenodes=self.apsimxml.findall(".//ini/filename")
        for cfn in cropfilenodes:
            cf=xml.etree.ElementTree.parse(cfn.text)
            cropfileparnodes=cf.findall(xpath)
            #print (str(len(cropfileparnodes))+"nodes found")
            for cfp,nt in zip(cropfileparnodes,itertools.cycle(newtexts)):
                if subelement is None:
                    cfp.text=nt
                else:
                    elements=re.split("\s+",cfp.text.strip())
                    elements[subelement]=nt
                    cfp.text=" ".join(elements)
            if (not overwrite_cropfile):
                rndstr=''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                newname=re.sub("(.*)\.xml$","\g<1>."+rndstr+".xml",cfn.text)
                self.set_sim_par(".//ini/filename",newname)
            else: 
                newname=cfn.text
            cf.write(newname)
        return (self.save(overwrite=overwrite_apsimfile))
        pass
    
    def get_results(self):
        pass
        
