
#added July 19,2024 by Modeste

'''the goal of the pipes classes is to define a series of cylindrical volumes, then take as an input a patch.py coilset, process over it, identify interference between the coil and pipes and then reroute the coils appropriately

Based on but not backward compatible with pipes.py created by Jeff Martin.

reroute_wires(self,coils,pipe_density=14) is the function that performs the re-routing.
  - the process requires closed loops to place the re-routes, so it uses make_closed() to do that.
  
QuickPipes() is a list of the standard pipes for the coil, run it before reroute_wires() to populate the list of pipes to re-reoute around.

create by M. McCrea

Process:
1. Make a pipelist
2. Add pipes to pipe list
3. Run pipelist.reroute(all_coil_list)
4. the current pipes are added to newpipes, and checked for intersects and re-routed.
5. if re-routes are made then make a larger new pipes for each re-route and repeat until no more re-routes are made.

sparsepipe does not do the newpipe rechecking assuming no overlaps in wires.

N.B.: If the same pipelist object is re-run multiple times it will recreate every re-route.
A clear intersections code could be useful, but currently just remake the pipeslist using QuickPipes.
'''
import numpy as np
from scipy.constants import mu_0, pi
import numpy as np
from numpy import sqrt,cos,sin
import math

class pipe:
    '''
      The pipe class allows for checking if a straight line parallel to either the x,y, or z axis, as defined by haxis, offset by a height vpipe in the direction given by vaxis, if it intersects with a circle in the plane defined by the two axis it will add a re-route.
      
       _     ^ v-axis
    --/-\--  |-> h-axis
      \_/
       Note: This code is limited in that the lines must approach along the given horizontal axis as diagrammed above with the ----- line crossing the circle, and line segments must not end inside the circle.
    '''
    def __init__(self,rpipe,hpipe,vpipe,haxis,vaxis,p_min=0,p_max=0,color=None):
        self.name = None
        self.color = color

        self.rpipe=rpipe #radius
        self.vpipe=vpipe #vertical position
        self.hpipe=hpipe #horizontal position
        self.haxis=haxis # 'x', 'y', or 'z' , the real axis for the horizontal direction
        self.vaxis=vaxis # 'x', 'y', or 'z', the real axis for the vertical direction
        #min and max distances along the axis perpendicular to the v and h axes to check for intersections and draw distance.
        self.pmin = p_min
        self.pmax = p_max
        self.inters = []  #list of pipe_intersects() class objects that collects the intersecting lines for the pipe
        
        #determine axis directions
        if self.vaxis == "x":
            self.index_v  = 0
        elif self.vaxis == "y":
            self.index_v  = 1
        elif self.vaxis == "z":
            self.index_v  = 2
        if self.haxis == "x":
            self.index_h  = 0
        elif self.haxis == "y":
            self.index_h  = 1
        elif self.haxis == "z":
            self.index_h  = 2
        #set the perpendicular axis to the axis not used for the other two.
        self.index_p = [value for value in [0,1,2] if (value != self.index_h and value !=self.index_v)][0]
        
    def __str__(self):
        #sets results when an object of the class is used in print()
        return "class pipe,name=%s, cntr = (%f,%f), rad=%f , haxis= %s, vaxis = %s, height=%f to %f intersects = %i"%(self.name,self.hpipe,self.vpipe,self.rpipe,self.haxis,self.vaxis,self.pmin,self.pmax,len(self.inters))

    def check_intersect(self,line):
        '''
            checks the intersection of a line with the pipe.
            
            assumes the central axis of the pipe and the wire plane are perpendicular and the wire is along the horizontal axis of the pipe.
            
            returns true if intersects, false if it does not.
        '''
        # trouble shooting diagnostics
        # print(self)
        # print("index_h = " , self.index_h)
        # print("index_v = " , self.index_v)
        # print("index_p = " , self.index_p)
        # print("vertical:" , self.vpipe-self.rpipe, line[0,self.index_v] , self.vpipe+self.rpipe)
        # print("horizontal:" , self.hpipe-self.rpipe, line[0,self.index_v] , self.hpipe+self.rpipe)
        # print("line = " , line)

        
        if np.array_equal(line[0],line[1]):
            #if point is itself, don't check for intersections.
            return False

        #if the point is the correct plane
        if(abs(line[0,self.index_p] - line[-1,self.index_p])<0.000001):
            #if the line doesn't overlap the height of the cylinder
            if line[0,self.index_p] < self.pmin or line[0,self.index_p] > self.pmax:
                # print("outside axial ends of cylinder")
                return False
            # if the point has the correct height
            # print("height check = " , line[0,self.index_v]<self.vpipe+self.rpipe, " and " , line[0,self.index_v]>self.vpipe-self.rpipe)
            if(line[0,self.index_v]<self.vpipe+self.rpipe and line[0,self.index_v]>self.vpipe-self.rpipe):
                #if it is prefered that the line must either start or end outside the circle:( untested code)
                # if (np.square(line[0,self.index_h]-self.hpipe)+np.square(line[0,self.index_v]-self.vpipe))<np.square(self.rpipe) or (np.square(line[1,self.index_h]-self.hpipe)+np.square(line[1,self.index_v]-self.vpipe))<np.square(self.rpipe):
                    # print("line inside circle")
                    # return False
                #and opposite sides of it along the horizontal:
                # if line[0,self.index_h]>(self.hpipe+self.rpipe) and line[1,self.index_h]>(self.hpipe-self.rpipe):
                    # print("line behind circle")
                    # return False
                # if (line[0,self.index_h]<(self.hpipe+self.rpipe) and line[1,self.index_h]<(self.hpipe-self.rpipe)):
                    # print("line in front of circle")
                    # return False
                # print("   check_intersect:intersection found")
                return True
        # print("general failure to intersect")
        return False


    def reroute_wire(self,pipe_density=4):#14):
        '''
        after pipelist:check_intersects() has been used this function will re-route around all intersections identified for this pipe.
        
        plane_min != plane_max, only re-route wires in that given plane.
        '''
        
        # print("\nstart reroute_wire")
        #no intersects, nothing to do, exit function 
        if len(self.inters)==0:
            # print("   0 wires intersected pipe")
            return 0,0


        pipenew = pipelist()#list of new pipes to check intersections based on re-routed wire paths
        #one or more coil loops or lines in a loop intersect a given pipe:
        loops = []
        lines = []
        delta_v = []
        planes = []
        for inter in self.inters:
            inter.coil.rerouted = inter.coil.rerouted+1 #indicate wire has been re-routed.
            for i1p1,i1p2 in zip(inter.points1,inter.points2):
                loops.append(inter.coil)
                lines.append(np.array([i1p1,i1p2]))
                delta_v.append(i1p1[self.index_v] - self.vpipe)
                planes.append(i1p1[self.index_p])
        
        sort_index = np.argsort(delta_v)

        # print("loops =\n " , loops)
        # print("lines =\n " , lines)
        # print("delta_v =\n " , delta_v)
        # print("planes =\n " , planes)
        # print("np.argsort(delta_v) = " , np.argsort(delta_v))
        sorting = np.argsort(delta_v)
        loops = np.array(loops)[sorting]
        lines = np.array(lines)[sorting]
        delta_v = np.array(delta_v)[sorting]
        planes = np.array(planes)[sorting]
        # print("sorted")
        # print("loops =\n " , loops)
        # print("lines =\n " , lines)
        # print("delta_v =\n " , delta_v)
        # print("planes =\n " , planes)
        
        
        # find all intersection lines in the same plane
        for pl in np.unique(planes):
            loopst = loops[pl==planes]
            linest = lines[pl==planes]
            delta_vt = delta_v[pl==planes]
            # print("pipe:reroute: pl = " , pl)
            # print("pl==planes = " , pl==planes)
            # print("loopst.size = " , loopst.size)
            # print("linest.size = " , linest.size)
            # print("loopst = " , loopst)
            # print("linest = " , linest)
            
            #for rerouting split into reroutes going over and under
            loopUnder = loopst[delta_vt<=0]
            lineUnder = linest[delta_vt<=0]
            loopOver = loopst[delta_vt>0]
            lineOver = linest[delta_vt>0]
            # print("pl = " , pl)
            # print("loopOver.size = " , loopOver.size)
            # print("lineOver.size = " , lineOver.size)
            # print("loopOver = " , loopOver[::-1])
            # print("lineOver = " , lineOver[::-1])
            wire_space = 0.0055
            rad_add_over = 0
            for loop,line in zip(loopOver,lineOver):
                # print("over: loop = " , loop)
                # print("over: len loop = " , len(loop.points))
                # print("over: ndim loop = " , loop.points.ndim)
                # print("over: loop = " , loop.points)
                # print("over: line = \n" , line)
                # print("over: rad_add_over = " , rad_add_over)
                self.insert_arc_points(loop,line,rad_add_over,pipe_density=pipe_density)
                rad_add_over=rad_add_over+wire_space
                # print("over:inserted loop = " , loop.points)
                # print()
                # input("Press Enter to continue...")
            # print("loopUnder.size = " , loopUnder.size)
            # print("lineUnder.size = " , lineUnder.size)
            # print("loopUnder = " , loopUnder[::-1])
            # print("lineUnder = " , lineUnder[::-1])
            rad_add_under = 0
            for loop,line in zip(loopUnder[::-1],lineUnder[::-1]):
                # print("under: loop = " , loop)
                # print("under: loop = " , loop.points)
                # print("under: line = \n" , line)
                # print("under: rad_add_under = " , rad_add_under)
                self.insert_arc_points(loop,line,rad_add_under,pipe_density=pipe_density)
                rad_add_under=rad_add_under+wire_space
                # print("under:inserted loop = " , loop.points)
                # print()
            #make new pipe to encompass newly re-routed wires
            
            if rad_add_over != 0 or rad_add_under !=0:
                rad_add = max(rad_add_over,rad_add_under)
                pipenew.add_pipe(self.rpipe+rad_add,
                                 self.vpipe,
                                 self.hpipe,
                                 self.haxis,
                                 self.vaxis,
                                 line[0,self.index_p]-0.0000001,
                                 line[0,self.index_p]+0.0000001)
        #sorting reroutes between end points of lines
        for loop,line in zip(loops,lines):
            self.sort_between_ends(loop,line)
            
        return len(self.inters),pipenew
        
    def gen_arc_points(self,line,radius, pipe_density = 4):#14):
      '''
      taking a pipe object from pipes.py and line defined by an two points in an array of 3d points as used in patch.py, create a numpy array of a circular arc 
      pipe_density = number of points around primary arc
      
      returns points to be inserted into loop.
      '''
      h_around=[] #horizontal motion
      v_around=[] #vertical motion
      p_around=[] #in plane coordinates
      
      #load pipe information
      rpipe = radius
      hpipe = self.hpipe
      vpipe = self.vpipe
      index_h  = self.index_h
      index_v  = self.index_v
      
      #check if re-route needs to be created
      #if(line[0,index_v]<vpipe+rpipe and line[0,index_v]>vpipe-rpipe):
      p_around=[line[0,self.index_p]]*pipe_density #coordinate in plane is constant
      #start calculating 2D point locations for shortest path around pipe:
      if(line[0,index_v]>vpipe): # if above center, go around the top side
        # print("gen_arc_points: going over")
        theta_start=math.atan2(line[0,index_v]-vpipe,sqrt(rpipe**2-(line[0,index_v]-vpipe)**2))
        theta_end=math.pi-theta_start
        theta_around=[theta_start+(theta_end-theta_start)*i/(pipe_density-1) for i in range(0,pipe_density)]
        v_around=vpipe+rpipe*sin(theta_around)
      else: # go around the bottom side if below or equal
        # print("gen_arc_points: going under")
        theta_start=math.atan2(vpipe-line[0,index_v],sqrt(rpipe**2-(line[0,index_v]-vpipe)**2))
        theta_end=math.pi-theta_start
        theta_around=[theta_start+(theta_end-theta_start)*i/(pipe_density-1) for i in range(0,pipe_density)]
        v_around=vpipe-rpipe*sin(theta_around)
      
      h_around=hpipe+rpipe*cos(theta_around)
      
      #recombine into [x,y,z] points appropriately for the horizontal and vertical axes:
      if self.haxis == "x":
        if self.vaxis == "y":
          new_arc = np.array([h_around, v_around, p_around])
        if self.vaxis == "z":
          new_arc = np.array([h_around, p_around, v_around])
      if self.haxis == "y":
        if self.vaxis == "x":
          new_arc = np.array([v_around, h_around, p_around])
        if self.vaxis == "z":
          new_arc = np.array([p_around, h_around, v_around])
      if self.haxis == "z":
        if self.vaxis == "x":
          new_arc = np.array([v_around, p_around, h_around])
        if self.vaxis == "y":
          new_arc = np.array([p_around, v_around, h_around])
      new_arc = np.transpose(new_arc.reshape(3,-1))
      
      #return new arc ensuring start point is closer first point than second point in line to keep direction correct.
      
      #diagnostic checks, uncomment for testing.
      
      # print("line = " , line)
      # print("rpipe = " , rpipe)
      # print("hpipe = " , hpipe)
      # print("vpipe = " , vpipe)
      # print("haxis = " , self.haxis)
      # print("vaxis = " , self.vaxis)
      
      # print("index_h = " , index_h)
      # print("index_v = " , index_v)
      # print("line[0,index_v] = " , line[0,index_v])
      # print("line[0,index_h] = " , line[0,index_h])
        
      # print("h_around = " , h_around)
      # print("v_around = " , v_around)
      # print("p_around = " , p_around)
      
      # print("distance to start " , np.linalg.norm(line[0,:]-new_arc[0,:]))
      # print("distance to end " , np.linalg.norm(line[0,:]-new_arc[-1,:]))
      
      
      if(np.linalg.norm(line[0,:]-new_arc[0,:]) > np.linalg.norm(line[0,:]-new_arc[-1,:])):
        #print("true, flipped")
        return np.flip(new_arc,axis=0)
      else:
        #print("unflipped")
        return new_arc
    
    def insert_arc_points(self,loop,line,rad_add,pipe_density=14):
        new_arc = self.gen_arc_points(line=line,radius=self.rpipe+rad_add,pipe_density=pipe_density)
        
        #remove points from outside the original line from the arc
        line_start = min(line[0, self.index_h],line[-1, self.index_h])
        line_end = max(line[0, self.index_h],line[-1, self.index_h])
        bool_diag = False
        if np.any(np.logical_and(new_arc[:,self.index_h]>line_start, new_arc[:,self.index_h]<line_end)):
            # bool_diag = True
            # print("line = \n" , line)
            # print("line_start = " , line_start)
            # print("line_end = " , line_end)
            # print("new_arc = " , new_arc)
            # print("new_arc[:,self.index_h]>line_start = " , new_arc[:,self.index_h]>line_start)
            # print("new_arc[:,self.index_h]<line_end = " , new_arc[:,self.index_h]<line_end)
            # print("np.and = " , np.logical_and(new_arc[:,self.index_h]>line_start, new_arc[:,self.index_h]<line_end))
            new_arc = new_arc[np.logical_and(new_arc[:,self.index_h]>line_start, new_arc[:,self.index_h]<line_end)]
            # print("new_arc shortened = " , new_arc , "\n")
        
        ind = np.where((loop.points == line[0]).all(axis=1))[0][0]
        # print("loop = " , loop)
        # print("loop.points =\n" , loop.points)
        # print("line = " , line)
        # print("ind = " , ind)
        # print("full = \n" , full)
        # print("self.gen_arc_points(line=line,radius=self.rpipe+rad_add) =\n" , new_arc)
        #add arc to loop
        loop.points = np.insert(
            loop.points,
            ind+1,
            new_arc,
            axis=0)
        # if bool_diag:print("loop.points after = \n" , loop.points)
    
    def sort_between_ends(self,loop,line):
        '''
        takes as an input a line segment, and sorts all points between the endpoints along one axis to make that line either uniformly increasing or decreasing
        '''
        if np.all(line[0]==loop.points[0]): #check if line starts at begining of loop, and use that as the index to prevent np.where confusion with closed loop.
            start = 0
        else:
            start = np.where((loop.points == line[0]).all(axis=1))[0][0]
        # print("start = " , start)
        if np.all(line[1]==loop.points[-1]):#deal with end of line being end of closed loop
            end = len(loop.points)
        else:
            end = np.where((loop.points == line[1]).all(axis=1))[0][0]
        # print("end = " , end)
        
        resort = loop.points[start+1:end]
        #if there are inserted points between the line segment endpoints, sort them along the horizontal axis:
        if not len(resort) == 0:
            resort = resort[resort[:, self.index_h].argsort()]
            #if ascending sort is incorrect, flip to descending
            if(np.linalg.norm(line[0,:]-resort[0,:]) > np.linalg.norm(line[0,:]-resort[-1,:])):
                # print("need to invert order")
                # print("resorting resort = \n" , np.flip(resort,axis=0))
                resort = np.flip(resort,axis=0)
            loop.points[start+1:end] = resort
        
    def draw_pipe(self,ax,trans=0.2, div_length = 2, div_rad = 14,**kwargs):
      '''
      on the given matplotlib axis ax, draws the cyinder for the pipe in the given transparanecy, color, and divisions of line segments.
      The div arguments give the number of flat panels to divide the circle into.
      '''
      #create cylinder along z-axis
      theta = np.linspace(0, 2*np.pi, div_rad)
      length = np.linspace(self.pmin, self.pmax, div_length)
      theta_grid, h_grid=np.meshgrid(theta, length)
      xs = self.rpipe*np.cos(theta_grid)
      ys = self.rpipe*np.sin(theta_grid)
      zs = h_grid
      # print(" xs = \n" , xs)
      # print(" ys = \n" , ys)
      # print(" zs = \n" , zs)
      
      if self.index_p == 0:
          if self.haxis == "y":
              ax.plot_surface(zs, xs+self.hpipe, ys+self.vpipe,alpha=trans,c=self.color,**kwargs)
          if self.haxis == "z":
              ax.plot_surface(zs, xs+self.vpipe, ys+self.hpipe,alpha=trans,c=self.color,**kwargs)
      if self.index_p == 1:
          cyl= np.array([xs,zs,ys])
          if self.haxis == "x":
              ax.plot_surface(xs+self.hpipe, zs, ys+self.vpipe,alpha=trans,c=self.color,**kwargs)
          if self.haxis == "z":
              ax.plot_surface(xs+self.vpipe, zs, ys+self.hpipe,alpha=trans,c=self.color,**kwargs)
      if self.index_p == 2:
          cyl= np.array([xs,ys,zs])
          if self.haxis == "x":
              ax.plot_surface(xs+self.hpipe, ys+self.vpipe, zs,alpha=trans,c=self.color,**kwargs)
          if self.haxis == "y":
              ax.plot_surface(xs+self.vpipe, ys+self.hpipe, zs,alpha=trans,c=self.color,**kwargs)
      

      return 1

class pipe_intersects:
    '''
    A list of lines segments from one coil that intersect the pipe to which this is attached.
    Used to store the output of check_intersects() and then read by reroute_wire() to make the required wire re-routes.
    '''
    def __init__(self,coil):
        self.coil = coil  #mutable coil loop link
        self.points1 = [] #first point in intersecting line
        self.points2 = [] #second point in intersecting line
    #def __str__(self):
    
    def add_inter(self, point1, point2):
        '''
        add a line segment from the given coil for the associated pipe.s
        '''
        self.points1.append(point1)
        self.points2.append(point2)

class pipelist:
    '''
    class for having a list of pipes and managing their properties with respect to a coil
    '''
    def __init__(self):
        self.pipes=[] #list of pipes to be checked
        self.npipes=len(self.pipes)

    def __str__(self):
        return "class pipelist\n    num_pipes = %i\n    id = %i"%(self.npipes,id(self))

    def add_pipe(self,rpipe,vpipe,hpipe,axish,axisv,pmin,pmax,color=None):
        newpipe=pipe(rpipe,vpipe,hpipe,axish,axisv,pmin,pmax,color=color)
        self.pipes.append(newpipe)
        self.npipes=len(self.pipes)
        
    def join_lists(self,new_pipes):
        for pipe in new_pipes.pipes:
            self.add_pipe(pipe.rpipe,pipe.vpipe,pipe.hpipe,pipe.haxis,pipe.vaxis,pipe.pmin,pipe.pmax)
        
    def list_pipes(self):
        print(self)
        for pipe in self.pipes:
            print("   " , pipe)

    def set_colors(self, color):
        print(self)
        for pipe in self.pipes:
            pipe.color=color

    def draw_pipes(self,pltax,**kwargs):
        for pipe in self.pipes:
            pipe.draw_pipe(pltax,**kwargs)
            
    def draw_xy(self,ax,div_rad = 14,text=False,**plt_kwargs):
        for pipe in self.pipes:
            if pipe.index_p == 2: #only pipes  with axis perpendicular to draw plane
                theta = np.linspace(0, 2*np.pi, div_rad)
                theta_grid = np.meshgrid(theta)[0]
                xs = pipe.rpipe*np.cos(theta_grid)
                ys = pipe.rpipe*np.sin(theta_grid)
                if pipe.haxis == "x":
                    ax.plot(xs+pipe.hpipe,ys+pipe.vpipe,color=pipe.color,**plt_kwargs)
                    if text:ax.annotate("(%.4f,%.4f)"%(pipe.hpipe,pipe.vpipe),xy=(pipe.hpipe,pipe.vpipe))
                if pipe.haxis == "y":
                    ax.plot(xs+pipe.vpipe,ys+pipe.hpipe,color=pipe.color,**plt_kwargs)
                    if text:ax.annotate("(%.4f,%.4f)"%(pipe.vpipe,pipe.hpipe),xy=(pipe.vpipe,pipe.hpipe))
            ax.set_xlabel('x (m)')
            ax.set_ylabel('y (m)')
    def draw_yz(self,ax, div_rad = 14,text=False,**plt_kwargs):
        for pipe in self.pipes:
            if pipe.index_p == 0: #only pipes  with axis perpendicular to draw plane
                theta = np.linspace(0, 2*np.pi, div_rad)
                theta_grid = np.meshgrid(theta)[0]
                ys = pipe.rpipe*np.cos(theta_grid)
                xs = pipe.rpipe*np.sin(theta_grid)
                if pipe.haxis == "z":
                    ax.plot(xs+pipe.vpipe,ys+pipe.hpipe,color=pipe.color,**plt_kwargs)
                    if text:ax.annotate("(%.4f,%.4f)"%(pipe.vpipe,pipe.hpipe),xy=(pipe.vpipe,pipe.hpipe))
                if pipe.haxis == "y":
                    ax.plot(xs+pipe.hpipe,ys+pipe.vpipe,color=pipe.color,**plt_kwargs)
                    if text:ax.annotate("(%.4f,%.4f)"%(pipe.hpipe,pipe.vpipe),xy=(pipe.hpipe,pipe.vpipe))
            ax.set_xlabel('y (m)')
            ax.set_ylabel('z (m)')
            
    
    def draw_xz(self,ax, div_rad = 14,text=False,**plt_kwargs):
        for pipe in self.pipes:
            if pipe.index_p == 1: #only pipes  with axis perpendicular to draw plane
                theta = np.linspace(0, 2*np.pi, div_rad)
                theta_grid = np.meshgrid(theta)[0]
                xs = pipe.rpipe*np.cos(theta_grid)
                ys = pipe.rpipe*np.sin(theta_grid)
                if pipe.haxis == "x":
                    ax.plot(xs+pipe.hpipe,ys+pipe.vpipe,color=pipe.color,**plt_kwargs)
                    if text:ax.annotate("(%.4f,%.4f)"%(pipe.hpipe,pipe.vpipe),xy=(pipe.hpipe,pipe.vpipe))
                if pipe.haxis == "z":
                    ax.plot(xs+pipe.vpipe,ys+pipe.hpipe,color=pipe.color,**plt_kwargs)
                    if text:ax.annotate("(%.4f,%.4f)"%(pipe.vpipe,pipe.hpipe),xy=(pipe.vpipe,pipe.hpipe))
            ax.set_xlabel('x (m)')
            ax.set_ylabel('z (m)')
    def draw_layout(self,fig,div_rad=14,**plt_kwargs):
        '''
        drawings front, side, top, and isometric view on the passed figure.
        the built in figure axes list must be either blank in which case 4 subplots are added, or if there are 4 axis, draws on them
        no error handling for bad cases is included.
        '''
        if not fig.axes:
            ax3=[]
            ax3.append(fig.add_subplot(2, 2, 3)) #lower left, xy-plane
            ax3.append(fig.add_subplot(2, 2, 4)) #lower right,yz-plane
            ax3.append(fig.add_subplot(2, 2, 1)) #upper left, xz-plane
            ax3.append(fig.add_subplot(2, 2, 2, projection='3d')) #upper right isometric view
        else:
            ax3 = fig.axes
        self.draw_xz(ax3[0],div_rad=div_rad,**plt_kwargs)
        self.draw_zy(ax3[1],div_rad=div_rad,**plt_kwargs)
        self.draw_xy(ax3[2],div_rad=div_rad,**plt_kwargs)
        self.draw_pipes(ax3[3],**plt_kwargs)
        return ax3

    def check_intersects(self,coils,level=0,plane=0):
        '''
        for each coil go through all pipe and for each coil loop in a coil set (coils) add intersect to each pipe
        '''
        # print("Starting pipelist:check_intersects of ", len(self.pipes), " pipes.")
        for index, pipe in enumerate(self.pipes):
            # print("pipelist:check_intersects: pipe " , index," of ", len(self.pipes))
            # print("pipelist:check_intersects: Total Coils = " ,len(coils.coils))
            for index, coil in enumerate(coils.coils):
                # if index%5 ==0:#uncomment to print current coils coil being processed.
                    # print(index,end=" ")
                # print("coil = " , coil)
                # print("coil.rerouted = " , coil.rerouted)
                if coil.rerouted == level:
                    add_flag = False
                    coil_ints = pipe_intersects(coil)
                    for j in range(len(coil.points)-1): #for closed loops
                        line = [coil.points[j],coil.points[j+1]]
                        # print("      line[0] = " , line[0])
                        # print("      line[1] = " , line[1])
                        if abs(line[0][pipe.index_p] - plane)<0.00001:
                            if np.all(line[0] == line[1]):
                                continue #skip repeated points
                            if pipe.check_intersect(np.array(line)):
                                # print("      intersection found")
                                add_flag = True
                                coil_ints.add_inter(line[0],line[1])
                        # else:
                            # print("Wrong Plane")
                    if add_flag:
                        pipe.inters.append(coil_ints)
                        # print("        check_intersects: pipe.inters added")
    
    def reroute_wires(self,coils,pipe_density=14):
        '''
        performs the re-routing for all pipes that have flagged intersects from check_intersects that must be run first.
        -!-!-!-!-!- note: the wire planes to reroute on must be set here.
        -!-!-!-!-!- changing the coil size requires the planes to be changed as well.
        '''
        # print("pipelist:reroutewires - starting fuction")
        #clean up coils to prepare for checking for intersections
        coils.make_closed() #first and last point in last made the same if not already
        coils.round_all() #round some decimal places for easier float comparisons
        
        #pl sets the plane positions to check for re-routes along the plane perpendicular to the axis of each cylindrical pipe.
        #I think this was done to prevent secondary re-routes from occuring on planes that don't contact each other.
        
        # for pl in [-1.906/2-0.087, -1.906/2, 1.906/2, 1.906/2+0.087,1.01]:
        # print("      pipelist.reroute_wires() - starting planes iteration: plane=", end =" ")
        for pl in [-2.1102/2, -1.9202/2, 1.9202/2, 2.1102/2]:#curent good
        # for pl in [2.1102/2]:
            # print(pl ,end= " , ")
            #reset variables for new plane.
            newpipes = [] # list of larger pipes for rerouting around re-routes
            for coil in coils.coils:
                coil.rerouted=0
            newpipes.append(self)
            go_on = True
            counter = 0
            
            #reroute wires and continue to do so until a rerouting makes no changes.
            while go_on:
                # print("pipelist:reroutewires - starting go_on loop")
                # print("- - - -pl = " , pl , ":  start loop = " , counter , "\n\n")
                newpipes[-1].check_intersects(coils, level = 0,plane = pl)
                
                temp = pipelist()
                changes = 0 #track how many lines are changed
                # print("newpipes[-1] = " , newpipes[-1])
                for index, pipe in enumerate(newpipes[-1].pipes):
                    # print("pipelist:reroute_wires- enumerate newpipes " , index, " of " , len(self.pipes)-1)
                    # print("   pipe = " , pipe)
                    total_reroutes, temppipes = pipe.reroute_wire(pipe_density=pipe_density)
                    changes = changes + total_reroutes
                    # print("      Total Reroutes:" , total_reroutes)
                    if temppipes != 0:
                        temp.join_lists(temppipes)
                newpipes.append(temp)
                counter = counter+1
                go_on = False #uncomment this line to only do the first resets
                if changes == 0: go_on = False
                coils.remove_duplicate_points()
        #clean up after re-routing as coils are usually an open list assumed to be a closed loop.
        coils.remove_duplicate_points()
        coils.make_open()
        # print("  re-routes done.")
        
    def reroute_wires2(self,coils,pipe_density=14,planes=[-1.906/2-0.087, -1.906/2, 1.906/2, 1.906/2+0.087,1.01]):
        '''
        performs the re-routing for all pipes that have flagged intersects from check_intersects that must be run first.
        
        I think that this was the start of a re-write that wasn't completed.
        '''
        #clean up coils to prepare for checking for intersections
        coils.make_closed() #first and last point in last made the same if not already
        coils.round_all() #round some decimal places for easier float comparisons
        
        #pl sets the plane positions to check for re-routes along the plane perpendicular to the axis of each cylindrical pipe.
        #I think this was done to prevent secondary re-routes from occuring on planes that don't contact each other.
        
        for pl in planes:
            #reset variables for new plane.
            newpipes = []
            for coil in coils.coils:
                coil.rerouted=0
            newpipes.append(self)
            go_on = True
            counter = 0
            
            #reroute wires and continue to do so until a rerouting make not changes.
            while go_on:
                print("\n\n - - - -pl = " , pl , ":  start loop = " , counter , "\n\n")
                newpipes[-1].check_intersects(coils, level = 0,plane = pl)
                
                temp = pipelist()
                changes = 0 #track how many lines are changed
                print("newpipes[-1] = " , newpipes[-1])
                for index, pipe in enumerate(newpipes[-1].pipes):
                    print("pipelist:reroute_wires: pipe " , index, " of " , len(self.pipes)-1)
                    print("   pipe = " , pipe)
                    total_reroutes, temppipes = pipe.reroute_wire(pipe_density=pipe_density)
                    changes = changes + total_reroutes
                    print("      Total Reroutes:" , total_reroutes)
                    if temppipes != 0:
                        temp.join_lists(temppipes)
                newpipes.append(temp)
                counter = counter+1
                # go_on = False #uncomment this line to only do the first resets
                if changes == 0 :go_on = False
        
        #clean up after re-routing as coils are usually an open list assumed to be a closed loop.
        coils.make_open()
    
    def insert_arcs(self,coils):
        '''
        generate arcs without regard to actual placement requirements without overlap and  proper ordering.
        superseded by reroute_wires().
        '''
        coil_flag = []
        point_flag = []
        pipe_flag = []
        for pipe in self.pipes:
          print(pipe)
          for coil in coils:
            for line in zip(coil.points, np.roll(coil.points,-1,axis=0)):
              if pipe.check_intersect(np.array(line)):
                  coil_flag.append(coil)
                  pipe_flag.append(pipe)
                  print(line[0])
                  print("where = " , np.where((coil.points == line[0]).all(axis=1)))
                  #point_flag.append(np.where((coil.points == line[0]).all(axis=1)))
                  point_flag.append(line[0])
        for index,coil,pipe in zip(point_flag,coil_flag,pipe_flag):
          ind = np.where((coil.points == index).all(axis=1))
          #print("type arc:" , type(pipe.gen_arc_points(coil.points[ind])))
          print("type points:" , type(coil.points))
          #print("arc" , pipe.gen_arc_points(coil.points[ind]))
          print("points:" , coil.points)
          print("index = " , index)
          print("ind = " , ind)
          print(pipe)
          
          coil.points = np.insert(coil.points,ind[0]+1,pipe.gen_arc_points(coil.points[ind[0]]),axis=0,pipe_density=4)
          print("new points:\n" , coil.points)



class sparsepipe():
    '''
      The sparse pipes class is used to re-arrange pipes for wires that are sufficiently sparse that it is not required to consider two wires conflicting.
      It is currently only setup for back and front faces of the coil with horizontal axis equal x axis.
    '''
    def __init__(self,rpipe,hpipe,vpipe,haxis=0,vaxis=2,p_min=0,p_max=0,color=None):
        self.name = None
        self.color = color

        self.rpipe=rpipe #radius
        self.vpipe=vpipe #vertical position
        self.hpipe=hpipe #horizontal position
        self.haxis=haxis # 'x', 'y', or 'z' , the real axis for the horizontal direction
        self.vaxis=vaxis # 'x', 'y', or 'z', the real axis for the vertical direction
        #min and max distances along the axis perpendicular to the v and h axes to check for intersections and draw distance.
        self.pmin = p_min
        self.pmax = p_max
        self.inters = []  #list of pipe_intersects() class objects that collects the intersecting lines for the pipe
        
        #determine axis directions
        if self.vaxis == "x":
            self.index_v  = 0
        elif self.vaxis == "y":
            self.index_v  = 1
        elif self.vaxis == "z":
            self.index_v  = 2
        if self.haxis == "x":
            self.index_h  = 0
        elif self.haxis == "y":
            self.index_h  = 1
        elif self.haxis == "z":
            self.index_h  = 2
        #set the perpendicular axis to the axis not used for the other two.
        self.index_p = [value for value in [0,1,2] if (value != self.index_h and value !=self.index_v)][0]
        
    def __str__(self):
        #sets results when an object of the class is used in print()
        return "class sparsepipe,name=%s, cntr = (%f,%f), rad=%f , haxis= %s, vaxis = %s, height=%f to %f intersects = %i"%(self.hpipe,self.vpipe,self.rpipe,self.haxis,self.vaxis,self.pmin,self.pmax,len(self.inters))

    def FaceReRoutes(self,points,pipe_density=14):
        '''
          takes a list 0f radii and then the x and z position on the back face and assumes wires coming across in the x direction.
          wires are assuming to be purely horizontal.
          wire segments are assumed to be outside the pipes.
          the goal of this is a simplified method of re-routing sparse wires for the back face re-routing.
          
          points is the open list assumed to make a closed loop
        '''
        #for each point pair
        # print("prints = " , points)
        # print("roll(points,-1,axis=0) = " , roll(points,-1,axis=0))
        newpoints = points
        # print("checking p0 to p1 lines: ")
        # for p0,p1 in zip(points, roll(points,-1,axis=0)):
            # print(p0 , " -> " , p1)
        for p0,p1 in zip(points, np.roll(points,-1,axis=0)):
            #check if a pipe intersects the line segment
            # print("p0=" , p0)
            # print("p1=" , p1)
            # print("abs(p0[1] - p1[1]) = " , abs(p0[1] - p1[1]))
            if(abs(p0[1] - p1[1])>0.000001): #if not on a y=constant plane, skip points
              continue;

            #new points to insert if intersect occurs.
            x_around=[]
            y_around=[]
            z_around=[]
            # print("p0[0]<hpipe-rpipe = " , p0[0]<self.hpipe-self.rpipe)
            # print("p1[0]>hpipe+rpipe = " , p1[0]>self.hpipe+self.rpipe)
            # print("p1[0]<hpipe-rpipe = " , p1[0]<self.hpipe-self.rpipe)
            # print("p0[0]>hpipe+rpipe = " , p0[0]>self.hpipe+self.rpipe)
            if(p0[0]<self.hpipe-self.rpipe and p1[0]>self.hpipe+self.rpipe) or (p1[0]<self.hpipe-self.rpipe and p0[0]>self.hpipe+self.rpipe): # end points are outside and on opp0site sides of feed through
                if(p0[2]<self.vpipe+self.rpipe and p0[2]>self.vpipe-self.rpipe):#if line between top and bottom of feed through
                    # print('Pipe intersection!')
                    # print("Intersect points = " , p0 , " and " , p1)
                    y_around=np.array([p0[1]]*pipe_density)
                    if(p0[2]>self.vpipe): # go around the top side
                        theta_start=math.atan2(p0[2]-self.vpipe,sqrt(self.rpipe**2-(p0[2]-self.vpipe)**2))
                        theta_end=pi-theta_start
                        theta_around=[theta_start+(theta_end-theta_start)*i/(pipe_density-1) for i in range(0,pipe_density)]
                        z_around=np.array(self.vpipe+self.rpipe*sin(theta_around))
                    else: # go around the bottom side
                        theta_start=math.atan2(self.vpipe-p0[2],sqrt(self.rpipe**2-(p0[2]-self.vpipe)**2))
                        theta_end=pi-theta_start
                        theta_around=[theta_start+(theta_end-theta_start)*i/(pipe_density-1) for i in range(0,pipe_density)]
                        z_around=np.array(self.vpipe-self.rpipe*sin(theta_around))
                    x_around=np.array(self.hpipe-self.rpipe*cos(theta_around))
                    #angles above don't care about direction along x-axis, so arrange start point to be closest to p0.
                    sort_ind = np.argsort(x_around)
                    # print("sort_ind = \n" , sort_ind)
                    # print("x_around = \n" , x_around)
                    # print("y_around = \n" , y_around)
                    # print("z_around = \n" , z_around)
                    if p0[0] < p1[0]: #incrementing
                        x_around=x_around[sort_ind]
                        y_around=y_around[sort_ind]
                        z_around=z_around[sort_ind]
                    else:#p0[0] > p1[0]
                        x_around=x_around[np.flip(sort_ind)]
                        y_around=y_around[np.flip(sort_ind)]
                        z_around=z_around[np.flip(sort_ind)]
                    ind = np.where((newpoints == p0).all(axis=1))[0][0]
                    newpoints = np.insert(
                        newpoints,
                        ind+1,
                        np.array([x_around,y_around,z_around]).T,
                        axis=0)
                    # print(points)
        return newpoints

    def draw_pipe(self,ax,trans=0.2, div_length = 2, div_rad = 14,**kwargs):
      '''
      on the given matplotlib axis ax, draws the cyinder for the pipe in the given transparanecy, color, and divisions of line segments.
      The div arguments give the number of flat panels to divide the circle into.
      '''
      #create cylinder along z-axis
      theta = np.linspace(0, 2*np.pi, div_rad)
      length = np.linspace(self.pmin, self.pmax, div_length)
      theta_grid, h_grid=np.meshgrid(theta, length)
      xs = self.rpipe*np.cos(theta_grid)
      ys = self.rpipe*np.sin(theta_grid)
      zs = h_grid
      # print(" xs = \n" , xs)
      # print(" ys = \n" , ys)
      # print(" zs = \n" , zs)
      
      if self.index_p == 0:
          if self.haxis == "y":
              ax.plot_surface(zs, xs+self.hpipe, ys+self.vpipe,alpha=trans,c=self.color,**kwargs)
          if self.haxis == "z":
              ax.plot_surface(zs, xs+self.vpipe, ys+self.hpipe,alpha=trans,c=self.color,**kwargs)
      if self.index_p == 1:
          cyl= np.array([xs,zs,ys])
          if self.haxis == "x":
              ax.plot_surface(xs+self.hpipe, zs, ys+self.vpipe,alpha=trans,c=self.color,**kwargs)
          if self.haxis == "z":
              ax.plot_surface(xs+self.vpipe, zs, ys+self.hpipe,alpha=trans,c=self.color,**kwargs)
      if self.index_p == 2:
          cyl= np.array([xs,ys,zs])
          if self.haxis == "x":
              ax.plot_surface(xs+self.hpipe, ys+self.vpipe, zs,alpha=trans,c=self.color,**kwargs)
          if self.haxis == "y":
              ax.plot_surface(xs+self.vpipe, ys+self.hpipe, zs,alpha=trans,c=self.color,**kwargs)

class sparsepipelist:
    '''
    class for having a list of pipes and managing their properties with respect to a coil
    '''
    def __init__(self):
        self.pipes=[] #list of pipes to be checked

    def __str__(self):
        return "class sparsepipelist\n    num_pipes = %i\n    id = %i"%(len(self.pipes),id(self))

    def add_pipe(self,rpipe,hpipe,vpipe,axish,axisv,pmin,pmax,color=None):
        self.pipes.append(sparsepipe(rpipe,hpipe,vpipe,axish,axisv,pmin,pmax,color=color))
        
    def join_lists(self,new_pipes):
        for pipe in new_pipes.pipes:
            self.add_pipe(pipe.rpipe,pipe.hpipe,pipe.vpipe,pipe.haxis,pipe.vaxis,pipe.pmin,pipe.pmax)
        
    def list_pipes(self):
        print(self)
        for pipe in self.pipes:
            print("   " , pipe)
    def reroute_wires(self,coils,pipe_density=14):
        '''
        performs the re-routing for all pipes
        '''
        for pipe in self.pipes:
            for coil in coils.coils:
                coil.points = pipe.FaceReRoutes(coil.points,pipe_density=pipe_density)
            
    def reroute_wires_list(self,all_coils_list,pipe_density=14):
        '''
        performs the re-routing for all pipes
        '''
        for coils in all_coils_list:
            self.reroute_wires(coils,pipe_density=pipe_density)

    def draw_pipes(self,pltax,**kwargs):
        for pipe in self.pipes:
            pipe.draw_pipe(pltax,**kwargs)
            
    def draw_xy(self,ax,div_rad = 14,text=False,**plt_kwargs):
        for pipe in self.pipes:
            if pipe.index_p == 2: #only pipes  with axis perpendicular to draw plane
                theta = np.linspace(0, 2*np.pi, div_rad)
                theta_grid = np.meshgrid(theta)[0]
                xs = pipe.rpipe*np.cos(theta_grid)
                ys = pipe.rpipe*np.sin(theta_grid)
                if pipe.haxis == "x":
                    ax.plot(xs+pipe.hpipe,ys+pipe.vpipe,color=pipe.color,**plt_kwargs)
                    if text:ax.annotate("(%.4f,%.4f)"%(pipe.hpipe,pipe.vpipe),xy=(pipe.hpipe,pipe.vpipe))
                if pipe.haxis == "y":
                    ax.plot(xs+pipe.vpipe,ys+pipe.hpipe,color=pipe.color,**plt_kwargs)
                    if text:ax.annotate("(%.4f,%.4f)"%(pipe.vpipe,pipe.hpipe),xy=(pipe.vpipe,pipe.hpipe))
            ax.set_xlabel('x (m)')
            ax.set_ylabel('y (m)')
    
    def draw_yz(self,ax, div_rad = 14,text=False,**plt_kwargs):
        for pipe in self.pipes:
            if pipe.index_p == 0: #only pipes  with axis perpendicular to draw plane
                theta = np.linspace(0, 2*np.pi, div_rad)
                theta_grid = np.meshgrid(theta)[0]
                ys = pipe.rpipe*np.cos(theta_grid)
                xs = pipe.rpipe*np.sin(theta_grid)
                if pipe.haxis == "z":
                    ax.plot(xs+pipe.vpipe,ys+pipe.hpipe,color=pipe.color,**plt_kwargs)
                    if text:ax.annotate("(%.4f,%.4f)"%(pipe.vpipe,pipe.hpipe),xy=(pipe.vpipe,pipe.hpipe))
                if pipe.haxis == "y":
                    ax.plot(xs+pipe.hpipe,ys+pipe.vpipe,color=pipe.color,**plt_kwargs)
                    if text:ax.annotate("(%.4f,%.4f)"%(pipe.hpipe,pipe.vpipe),xy=(pipe.hpipe,pipe.vpipe))
            ax.set_xlabel('y (m)')
            ax.set_ylabel('z (m)')
    
    def draw_xz(self,ax, div_rad = 14,text=False,**plt_kwargs):
        for pipe in self.pipes:
            if pipe.index_p == 1: #only pipes  with axis perpendicular to draw plane
                theta = np.linspace(0, 2*np.pi, div_rad)
                theta_grid = np.meshgrid(theta)[0]
                xs = pipe.rpipe*np.cos(theta_grid)
                ys = pipe.rpipe*np.sin(theta_grid)
                if pipe.haxis == "x":
                    ax.plot(xs+pipe.hpipe,ys+pipe.vpipe,color=pipe.color,**plt_kwargs)
                    if text:ax.annotate("(%.4f,%.4f)"%(pipe.hpipe,pipe.vpipe),xy=(pipe.hpipe,pipe.vpipe))
                if pipe.haxis == "z":
                    ax.plot(xs+pipe.vpipe,ys+pipe.hpipe,color=pipe.color,**plt_kwargs)
                    if text:ax.annotate("(%.4f,%.4f)"%(pipe.vpipe,pipe.hpipe),xy=(pipe.vpipe,pipe.hpipe))
            ax.set_xlabel('x (m)')
            ax.set_ylabel('z (m)')
    
    def draw_layout(self,fig,div_rad=14,**plt_kwargs):
        '''
        drawings front, side, top, and isometric view on the passed figure.
        the built in figure axes list must be either blank in which case 4 subplots are added, or if there are 4 axis, draws on them
        no error handling for bad cases is included.
        '''
        if not fig.axes:
            ax3=[]
            ax3.append(fig.add_subplot(2, 2, 3)) #lower left, xy-plane
            ax3.append(fig.add_subplot(2, 2, 4)) #lower right,yz-plane
            ax3.append(fig.add_subplot(2, 2, 1)) #upper left, xz-plane
            ax3.append(fig.add_subplot(2, 2, 2, projection='3d')) #upper right isometric view
        else:
            ax3 = fig.axes
        self.draw_xz(ax3[0],div_rad=div_rad,**plt_kwargs)
        self.draw_zy(ax3[1],div_rad=div_rad,**plt_kwargs)
        self.draw_xy(ax3[2],div_rad=div_rad,**plt_kwargs)
        self.draw_pipes(ax3[3],**plt_kwargs)
        return ax3


def TwoPipes(mypipes):
    '''
    quick creation of a small number of pipes for testing
    '''
    r_add = 0.000
    
    #side wall pipes
    rpipes=[0.02,0.02 #m
            ] #m
    ypipes=[ 0,0.1
            ] #m
    zpipes=[0,0
            ] #m
    
    rpipes = np.array(rpipes)+r_add
    for j in range(len(rpipes)):
        mypipes.add_pipe(rpipes[j],zpipes[j],ypipes[j],'y',"z",-1.21,1.21)

def QuickDefBack(mypipes, rad_add=0,color=None):
    '''
        Used for adding back wall pipes to pipeslist or sparsepipeslist.
    '''
    #----------------------------------------
    #back wall pipes
    gcc_x=0.62 #meter, guide center-to-center in horizontal direction
    gcc_y=.674 #meter, guide center-to-center in vertical (z) direction
    gdia=.1524+rad_add*2 #meter, guide diameter
    #center HV
    mypipes.add_pipe(gdia/2+0.02,0      ,0        ,'x','z',-1.21,-1.21)
    
    #mirrored 4 UCN feed thrus
    mypipes.add_pipe(gdia/2, gcc_x/2, gcc_y/2,"x",'z',-1.21,-1,color=color)
    mypipes.add_pipe(gdia/2, gcc_x/2,-gcc_y/2,"x",'z',-1.21,-1,color=color)
    mypipes.add_pipe(gdia/2,-gcc_x/2, gcc_y/2,"x",'z',-1.21,-1,color=color)
    mypipes.add_pipe(gdia/2,-gcc_x/2,-gcc_y/2,"x",'z',-1.21,-1,color=color)
    
    #Small feed throughs
    cdia = 0.06+rad_add*2#meter
    mypipes.add_pipe(cdia/2, 0.0   ,-0.140,"x",'z',-1.21,1.21,color=color)
    mypipes.add_pipe(cdia/2, 0.0   , 0.140,"x",'z',-1.21,1.21,color=color)
    mypipes.add_pipe(cdia/2,-0.140 , 0.0  ,"x",'z',-1.21,1.21,color=color)
    mypipes.add_pipe(cdia/2, 0.140 , 0.0  ,"x",'z',-1.21,1.21,color=color)

    mypipes.add_pipe(0.042/2,-0.20, 0.0,"x",'z',-1.21,1.21,color=color)
    mypipes.add_pipe(0.042/2, 0.20, 0.0,"x",'z',-1.21,1.21,color=color)
    
    #front wall feed throughs
    ctrdia = 0.040+rad_add*2#meter
    mypipes.add_pipe(ctrdia/2, 0.0   ,-0.140,"x",'z',1,1.21,color=color)
    mypipes.add_pipe(ctrdia/2, 0.0   , 0.140,"x",'z',1,1.21,color=color)
    mypipes.add_pipe(ctrdia/2,-0.140 , 0.0  ,"x",'z',1,1.21,color=color)
    mypipes.add_pipe(ctrdia/2, 0.140 , 0.0  ,"x",'z',1,1.21,color=color)
    
    #corner feed throughs
    cdia = 0.1016+rad_add*2#meter
    mypipes.add_pipe(cdia/2,-0.9 , 0.9 ,"x",'z',-1.21,1.21,color="olivedrab")
    mypipes.add_pipe(cdia/2, 0.9 , 0.9 ,"x",'z',-1.21,1.21,color="olivedrab")
    mypipes.add_pipe(cdia/2, 0.9 ,-0.9 ,"x",'z',-1.21,1.21,color="olivedrab")
    mypipes.add_pipe(cdia/2,-0.9 ,-0.9 ,"x",'z',-1.21,1.21,color="olivedrab")

def QuickDefWallReRoute(mypipes, rad_add=0,color=None):
    #side wall pipes
    #nominal feed through sizes,rad_add
    r3x5 =   0.001*(71)/2 + rad_add#0.001*(71+12.9)/2#m 71mm B0 form feed through, 2.9mm oversize
    rHg199 = 0.001*(35)/2 + rad_add#0.001*(35+12.9)/2#m
    rpipes=[
            r3x5,r3x5,r3x5,r3x5,r3x5,
                  rHg199,rHg199,
            r3x5,r3x5,r3x5,r3x5,r3x5,
                  rHg199,rHg199,
            r3x5,r3x5,r3x5,r3x5,r3x5,
            ] #meter
    ypipes=[
            -0.4,-0.4,-0.4,-0.4,-0.4,
                  0.14,0.185/2,
             0,   0,   0,   0,   0,
                  -0.14,-0.185/2,
             0.4, 0.4, 0.4, 0.4, 0.4,
            ] #meter
    zpipes=[
            -0.44,-0.20,0,0.20,0.44,
                       0,0,
            -0.44,-0.20,0,0.20,0.44,
                       0,0,
            -0.44,-0.20,0,0.20,0.44,
            ] #meter
    
    rpipes = np.array(rpipes)
    for j in range(len(rpipes)):
        mypipes.add_pipe(rpipes[j],zpipes[j],ypipes[j],'y',"z",-1.21,1.21,color=color)

def QuickDefWallPlotting(mypipes, rad_add=0,color=None):
    #side wall pipes taht are not to be re-routed
    #nominal feed through sizes,rad_add
        #----------------------------------------
    #side wall pipes
    #nominal feed through sizes,rad_add
    rCorner= 0.001*(101.6)/2#m
    
    rpipes=[rCorner,           rCorner,
            rCorner,           rCorner,
            rCorner,            rCorner,
            rCorner,           rCorner
            ] #meter
    ypipes=[1.050,            1.050,
            0.840,               0.840,
            -0.840,             -0.840,
            -1.050,             -1.050,
            ] #meter
    zpipes=[-0.840,               0.840,
            -1.050,            1.050,
            -1.050,            1.050,
            -0.840,               0.840
            ] #meter
    
    rpipes = np.array(rpipes)
    for j in range(len(rpipes)):
        mypipes.add_pipe(rpipes[j],zpipes[j],ypipes[j],'y',"z",-1.21,1.21,color="blue")

def QuickDefFloorReRoute(mypipes, rad_add=0,color=None):
    #floor supports
    rpipes_floor = [
                    0.04/2.0 ,          0.04/2.0 ,0.04/2.0 ,             0.04/2.0,
                           0.04/2.0 ,             0.04/2.0,
                    0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0,
                    0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0,
                    0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0,
                    0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0,
                           0.04/2.0 ,             0.04/2.0,
                    0.04/2.0 ,          0.04/2.0 ,0.04/2.0 ,             0.04/2.0,] #meter
    
    xpipes_floor = [
             -0.9025,           -0.9025,-0.9025,          -0.9025,
                            -0.775,         -0.775,
             -0.5025 ,-0.5025 ,-0.5025 ,-0.5025 ,-0.5025 ,-0.5025 ,
             -0.0625 ,-0.0625 ,-0.0625 ,-0.0625 ,-0.0625 ,-0.0625 ,
              0.0625 , 0.0625 , 0.0625 , 0.0625 , 0.0625 , 0.0625 ,
              0.5025 , 0.5025 , 0.5025 , 0.5025 , 0.5025 , 0.5025 ,
                             0.775,          0.775,
              0.9025,            0.9025, 0.9025,           0.9025]#meter
    
    ypipes_floor = [
            -0.9125 ,          -0.0675  , 0.0675,            0.9125,
                       -0.380 ,                  0.380,
            -0.9125 ,-0.4025 , -0.0675 , 0.0675 ,  0.4025 , 0.9125,
            -0.9125 ,-0.4025 , -0.0675 , 0.0675 ,  0.4025 , 0.9125,
            -0.9125 ,-0.4025 , -0.0675 , 0.0675 ,  0.4025 , 0.9125,
            -0.9125 ,-0.4025 , -0.0675 , 0.0675 ,  0.4025 , 0.9125,
                       -0.380 ,                  0.380,
            -0.9125,           -0.0675  , 0.0675,            0.9125]#meter
    #add pipes to list of pipes with added radius
    rpipes_floor = np.array(rpipes_floor)+.01+rad_add#m
    for rad,y,x in zip(rpipes_floor,ypipes_floor,xpipes_floor):
        mypipes.add_pipe(rad,x,y,'y','x',-1.21,1.21,color=color)
    #----------------------------------------
    #central 5 feedthrus
    rpipes_feedthru = [0.0697/2,0.0697/2,0.0697/2,0.0697/2,0.0697/2]#meter
    ypipes_feedthru=[-0.2, 0  ,0,0  ,0.2]#meter
    xpipes_feedthru=[ 0  ,-0.2,0,0.2,0  ]#meter
    rpipes_feedthru = np.array(rpipes_feedthru)+0.01#meter
    for rad,y,x in zip(rpipes_feedthru,ypipes_feedthru,xpipes_feedthru):
        mypipes.add_pipe(rad,x,y,'y','x',-1.21,1.21,color=color)


def QuickDefFloorPlotting(mypipes, rad_add=0,color=None):
    #floor supports for plotting only, outside B0 coil.
    rpipes_floor = [ 
                           0.04/2.0 ,             0.04/2.0,
                           0.04/2.0 ,             0.04/2.0] #meter
    
    xpipes_floor = [
                            -1.025,         -1.025,
                             1.025,          1.025]#meter
    
    ypipes_floor = [
                               -0.380 ,                  0.380,
                               -0.380 ,                  0.380]#meter
    #add pipes to list of pipes with added radius
    rpipes_floor = np.array(rpipes_floor)+.01+rad_add#m
    for rad,y,x in zip(rpipes_floor,ypipes_floor,xpipes_floor):
        mypipes.add_pipe(rad,x,y,'y','x',-1.21,1.21,color=color)

def QuickDefWallReRouteOvals(mypipes, rad_add=0,color=None):
    #large adjustment ovals
    
    #left right faces
    zpipes = [0.93431 , 0.83431, 0.59625, 0.37125, 0.11250, -0.11250, -0.37125, -0.59625, -0.83431, -0.93431]
    ypipes = [0.5850,-0.5850]
    oval_radius = 20.0/1000.0
    width = 60.0/1000.0
    for z in zpipes:
        mypipes.add_pipe(oval_radius,ypipes[0]+width/2,z,'y','z',-1.21,1.21,color=color)
        mypipes.add_pipe(oval_radius,ypipes[0]-width/2,z,'y','z',-1.21,1.21,color=color)
        mypipes.add_pipe(oval_radius,ypipes[1]+width/2,z,'y','z',-1.21,1.21,color=color)
        mypipes.add_pipe(oval_radius,ypipes[1]-width/2,z,'y','z',-1.21,1.21,color=color)
    #small attachment point ovals
    zpipes = [0.99681 , 0.77181, 0.65875, 0.30875, 0.1750,-0.175, -0.30875, -0.65875, -0.77181, -0.99681]
    oval_radius = 5.0/1000.0
    width = 50.0/1000.0
    for z in zpipes:
        mypipes.add_pipe(oval_radius,ypipes[0]+width/2,z,'y','z',-1.21,1.21,color=color)
        mypipes.add_pipe(oval_radius,ypipes[0]-width/2,z,'y','z',-1.21,1.21,color=color)
        mypipes.add_pipe(oval_radius,ypipes[1]+width/2,z,'y','z',-1.21,1.21,color=color)
        mypipes.add_pipe(oval_radius,ypipes[1]-width/2,z,'y','z',-1.21,1.21,color=color)
        
    #top and bottom faces
    zpipes = [0.81110 , 0.71110, 0.45256, 0.39756, -0.39756, -0.45256, -0.71110, -0.81110]
    ypipes = [0.5850,-0.5850]
    oval_radius = 20.0/1000.0
    width = 60.0/1000.0
    for z in zpipes:
        mypipes.add_pipe(oval_radius,ypipes[0]+width/2,z,'y','x',-1.21,1.21,color=color)
        mypipes.add_pipe(oval_radius,ypipes[0]-width/2,z,'y','x',-1.21,1.21,color=color)
        mypipes.add_pipe(oval_radius,ypipes[1]+width/2,z,'y','x',-1.21,1.21,color=color)
        mypipes.add_pipe(oval_radius,ypipes[1]-width/2,z,'y','x',-1.21,1.21,color=color)
    #small attachment point ovals
    zpipes = [0.87360 , 0.64860, 0.51506, 0.33506, -0.33506, -0.51506, -0.64860, -0.87360]
    oval_radius = 5.0/1000.0
    width = 50.0/1000.0
    for z in zpipes:
        mypipes.add_pipe(oval_radius,ypipes[0]+width/2,z,'y','x',-1.21,1.21,color=color)
        mypipes.add_pipe(oval_radius,ypipes[0]-width/2,z,'y','x',-1.21,1.21,color=color)
        mypipes.add_pipe(oval_radius,ypipes[1]+width/2,z,'y','x',-1.21,1.21,color=color)
        mypipes.add_pipe(oval_radius,ypipes[1]-width/2,z,'y','x',-1.21,1.21,color=color)
        
   
   
def OvalCleanUp(all_coil_list):
    #doing some extra clean up to remove points from middle oval faces

    #side walls
    zpipes = [0.93431 , 0.83431, 0.59625, 0.37125, 0.11250, -0.11250, -0.37125, -0.59625, -0.83431, -0.93431]
    ypipes = [0.5850,-0.5850]
    oval_radius = 20.0/1000.0
    width = 60.0/1000.0
    for section in all_coil_list:
        for z in zpipes:
            section.remove_points(xmin=-1.5,xmax=1.5, ymin=ypipes[0]-width/2+0.001,ymax=ypipes[0]+width/2-0.001, zmin=z-1.5*oval_radius,zmax=z+1.5*oval_radius, keep_size =1)
            section.remove_points(xmin=-1.5,xmax=1.5, ymin=ypipes[1]-width/2+0.001,ymax=ypipes[1]+width/2-0.001, zmin=z-1.5*oval_radius,zmax=z+1.5*oval_radius, keep_size =1)
    #small attachment point ovals
    zpipes = [0.99681 , 0.77181, 0.65875, 0.30875, 0.1750,-0.175, -0.30875, -0.65875, -0.77181, -0.99681]
    oval_radius = 5.0/1000.0
    width = 50.0/1000.0
    for section in all_coil_list:
        for z in zpipes:
            section.remove_points(xmin=-1.5,xmax=1.5, ymin=ypipes[0]-width/2+0.001,ymax=ypipes[0]+width/2-0.001, zmin=z-1.5*oval_radius,zmax=z+1.5*oval_radius, keep_size =1)
            section.remove_points(xmin=-1.5,xmax=1.5, ymin=ypipes[1]-width/2+0.001,ymax=ypipes[1]+width/2-0.001, zmin=z-1.5*oval_radius,zmax=z+1.5*oval_radius, keep_size =1)

    #floor and ceiling
    zpipes = [0.81110 , 0.71110, 0.45256, 0.39756, -0.39756, -0.45256, -0.71110, -0.81110]
    ypipes = [0.5850,-0.5850]
    oval_radius = 20.0/1000.0
    width = 60.0/1000.0
    for section in all_coil_list:
        for z in zpipes:
            section.remove_points(zmin=-1.5,zmax=1.5, ymin=ypipes[0]-width/2+0.001,ymax=ypipes[0]+width/2-0.001, xmin=z-1.5*oval_radius,xmax=z+1.5*oval_radius, keep_size =1)
            section.remove_points(zmin=-1.5,zmax=1.5, ymin=ypipes[1]-width/2+0.001,ymax=ypipes[1]+width/2-0.001, xmin=z-1.5*oval_radius,xmax=z+1.5*oval_radius, keep_size =1)
    #small attachment point ovals
    zpipes = [0.87360 , 0.64860, 0.51506, 0.33506, -0.33506, -0.51506, -0.64860, -0.87360]
    oval_radius = 5.0/1000.0
    width = 50.0/1000.0
    for section in all_coil_list:
        for z in zpipes:
            section.remove_points(zmin=-1.5,zmax=1.5, ymin=ypipes[0]-width/2+0.001,ymax=ypipes[0]+width/2-0.001, xmin=z-1.5*oval_radius,xmax=z+1.5*oval_radius, keep_size =1)
            section.remove_points(zmin=-1.5,zmax=1.5, ymin=ypipes[1]-width/2+0.001,ymax=ypipes[1]+width/2-0.001, xmin=z-1.5*oval_radius,xmax=z+1.5*oval_radius, keep_size =1)


def QuickPipes(pipesC, pipesS, rad_add=0,color=None):
    #Z should be vertical in the model.
    '''
    use this to add all feed thrus that coils should be re-routed around to a pair of pre-existing pipelists
    '''
    QuickDefWallReRoute(pipesC,rad_add,color=color)
    QuickDefFloorReRoute(pipesC,rad_add,color=color)
    QuickDefWallReRouteOvals(pipesC,0.0025,color=color)

    QuickDefBack(pipesS,rad_add,color=color)
    
    #return not required as inputs are mutable.
    # return pipesC, pipesS

def QuickFeedThroughs(pipesC, pipesS, rad_add=0,color=None):
    #Z should be vertical in the model.
    #looking only at feed throughs
    '''
    use this to add all feed thrus that coils should be re-routed around to a pair of pre-existing pipelists
    '''
    QuickDefWallReRoute(pipesC,0,color=color)
    QuickDefFloorPlotting(pipesC,0,color=color)
    QuickDefFloorReRoute(pipesC,0,color=color)
    QuickDefWallPlotting(pipesC,0,color=color)
    QuickDefBack(pipesS,0,color=color)
    
    #return not required as inputs are mutable.
    # return pipesC, pipesS

def QuickPipesPlotting(pipesC, pipesS, rad_add=0,color=None):
    #Z should be vertical in the model.
    '''
    use this to add all feed thrus that coils should not be re-routed around to a pair of pre-existing pipelists
    This is used in conjunction with QuickPipes to setup a pipeslist for plotting references.
    '''
    
    QuickDefWallPlotting(pipesC,rad_add,color=color)
    QuickDefFloorPlotting(pipesC,rad_add,color=color)
    
    return pipesC, pipesS

#old 100 mm layer 5 pipe re-routes
def QuickPipesOriginal(mypipes, rad_add=0):
    '''
    the standard MSR pipe layouts for easy reference
    use this to add all current feedthrus to a pipelist.
    '''
    
    '''
    #back wall pipes
    gcc_x=0.62 #meter, guide center-to-center in horizontal direction
    gcc_y=.674 #meter, guide center-to-center in vertical (z) direction
    gdia=.1524+0.05+rad_add #meter, guide diameter
    #center HV
    mypipes.add_pipe(gdia/2,0      ,0        ,'x','z',-1.21,1.21)
    #mirrored 4 UCN feed thrus
    mypipes.add_pipe(gdia/2, gcc_x/2, gcc_y/2,"x",'z',-1.21,1.21)

    mypipes.add_pipe(gdia/2, gcc_x/2,-gcc_y/2,"x",'z',-1.21,1.21)
    mypipes.add_pipe(gdia/2,-gcc_x/2, gcc_y/2,"x",'z',-1.21,1.21)
    mypipes.add_pipe(gdia/2,-gcc_x/2,-gcc_y/2,"x",'z',-1.21,1.21)
    
    #Small feed throughs
    cdia = 0.06+0.1+rad_add#meter
    mypipes.add_pipe(cdia/2, 0.0   ,-0.140,"x",'z',-1.21,1.21)
    mypipes.add_pipe(cdia/2, 0.0   , 0.140,"x",'z',-1.21,1.21)
    mypipes.add_pipe(cdia/2,-0.140 , 0.0  ,"x",'z',-1.21,1.21)
    mypipes.add_pipe(cdia/2, 0.140 , 0.0  ,"x",'z',-1.21,1.21)

    mypipes.add_pipe(0.042/2,-0.20, 0.0,"x",'z',-1.21,1.21)
    mypipes.add_pipe(0.042/2, 0.20, 0.0,"x",'z',-1.21,1.21)
    
    #corner feed throughs
    cdia = 0.1016+0.03+rad_add#meter
    mypipes.add_pipe(cdia/2, 0.0   ,-0.140,"x",'z',-1.21,1.21)
    mypipes.add_pipe(cdia/2, 0.0   , 0.140,"x",'z',-1.21,1.21)
    mypipes.add_pipe(cdia/2,-0.140 , 0.0  ,"x",'z',-1.21,1.21)
    mypipes.add_pipe(cdia/2, 0.140 , 0.0  ,"x",'z',-1.21,1.21)
    '''
    #side wall pipes
    #nominal feed through sizes,rad_add
    r3x5 =   0.001*(71+12.9)/2#m 71mm B0 form feed through, 2.9mm oversize
    rCorner= 0.001*(110+12.9)/2#m
    rHg199 = 0.001*(35+12.9)/2#m
    rpipes=[rCorner,           rCorner,
            r3x5,r3x5,r3x5,r3x5,r3x5,
                  rHg199,rHg199,
            r3x5,r3x5,r3x5,r3x5,r3x5,
                  rHg199,rHg199,
            r3x5,r3x5,r3x5,r3x5,r3x5,
            rCorner,            rCorner
            ] #meter
    ypipes=[ 0.840,               0.840,
            -0.4,-0.4,-0.4,-0.4,-0.4,
                  0.14,0.185/2,
             0,   0,   0,   0,   0,
                  -0.14,-0.185/2,
             0.4, 0.4, 0.4, 0.4, 0.4,
            -0.840,             -0.840
            ] #meter
    zpipes=[-1.050,            1.050,
            -0.44,-0.20,0,0.20,0.44,
                       0,0,
            -0.44,-0.20,0,0.20,0.44,
                       0,0,
            -0.44,-0.20,0,0.20,0.44,
            -1.050,            1.050
            ] #meter
    
    rpipes = np.array(rpipes)
    print("rpipes = " , rpipes)
    for j in range(len(rpipes)):
        mypipes.add_pipe(rpipes[j],zpipes[j],ypipes[j],'y',"z",-1.21,1.21)
    
    #floor supports
    rpipes_floor = [ 
                           0.04/2.0 ,             0.04/2.0,
                                 0.04/2.0 , 0.04/2.0,
                    0.04/2.0 ,                           0.04/2.0,
                           0.04/2.0 ,             0.04/2.0,
                    0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0,
                    0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0,
                    0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0,
                    0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0, 0.04/2.0 , 0.04/2.0,
                           0.04/2.0 ,             0.04/2.0,
                                 0.04/2.0 , 0.04/2.0,
                    0.04/2.0 ,                           0.04/2.0,
                           0.04/2.0 ,             0.04/2.0] #meter
    
    xpipes_floor = [
                            -1.025,         -1.025,
             -0.9025,           -0.9025,-0.9025,          -0.9025,
                            -0.775,         -0.775,
             -0.5025 ,-0.5025 ,-0.5025 ,-0.5025 ,-0.5025 ,-0.5025 ,
             -0.0625 ,-0.0625 ,-0.0625 ,-0.0625 ,-0.0625 ,-0.0625 ,
              0.0625 , 0.0625 , 0.0625 , 0.0625 , 0.0625 , 0.0625 ,
              0.5025 , 0.5025 , 0.5025 , 0.5025 , 0.5025 , 0.5025 ,
                             0.775,          0.775,
              0.9025,            0.9025, 0.9025,           0.9025,
                             1.025,          1.025]#meter
    
    ypipes_floor = [
                               -0.380 ,                  0.380,
                    -0.9125           -0.0675  , 0.0675,            0.9125,
                               -0.380 ,                  0.380,
                    -0.9125 ,-0.4025 , -0.0675 , 0.0675 ,  0.4025 , 0.9125,
                    -0.9125 ,-0.4025 , -0.0675 , 0.0675 ,  0.4025 , 0.9125,
                    -0.9125 ,-0.4025 , -0.0675 , 0.0675 ,  0.4025 , 0.9125,
                    -0.9125 ,-0.4025 , -0.0675 , 0.0675 ,  0.4025 , 0.9125,
                               -0.380 ,                  0.380,
                    -0.9125           -0.0675  , 0.0675,            0.9125,
                               -0.380 ,                  0.380]#meter
    #add pipes to list of pipes with added radius
    rpipes_floor = np.array(rpipes_floor)+.01+rad_add#m
    for rad,y,x in zip(rpipes_floor,ypipes_floor,xpipes_floor):
        mypipes.add_pipe(rad,x,y,'y','x',-1.21,1.21)
    #----------------------------------------
    #central 5 feedthrus
    rpipes_feedthru = [0.0697/2,0.0697/2,0.0697/2,0.0697/2,0.0697/2]#meter
    ypipes_feedthru=[-0.2,0,0,0,0.2]#meter
    xpipes_feedthru=[0,-0.2,0,0.2,0]#meter
    rpipes_feedthru = np.array(rpipes_feedthru)+0.01#meter
    for rad,y,x in zip(rpipes_feedthru,ypipes_feedthru,xpipes_feedthru):
        mypipes.add_pipe(rad,x,y,'y','x',-1.21,1.21)


'''backup copy of points in near orignal format
#plots all feed throughs even those not being re-reouted.
def QuickPipesPlotting(mypipes, rad_add=0):
    #----------------------------------------
    #back wall pipes
    gcc_x=0.62 #meter, guide center-to-center in horizontal direction
    gcc_y=.674 #meter, guide center-to-center in vertical (z) direction
    gdia=.1524+rad_add*2 #meter, guide diameter
    #center HV
    mypipes.add_pipe(gdia/2,0      ,0        ,'x','z',-1.21,-1)
    
    #mirrored 4 UCN feed thrus
    mypipes.add_pipe(gdia/2, gcc_x/2, gcc_y/2,"x",'z',-1.21,-1)
    mypipes.add_pipe(gdia/2, gcc_x/2,-gcc_y/2,"x",'z',-1.21,-1)
    mypipes.add_pipe(gdia/2,-gcc_x/2, gcc_y/2,"x",'z',-1.21,-1)
    mypipes.add_pipe(gdia/2,-gcc_x/2,-gcc_y/2,"x",'z',-1.21,-1)
    
    #Small feed throughs
    cdia = 0.06+rad_add*2#meter
    mypipes.add_pipe(cdia/2, 0.0   ,-0.140,"x",'z',-1.21,1.21)
    mypipes.add_pipe(cdia/2, 0.0   , 0.140,"x",'z',-1.21,1.21)
    mypipes.add_pipe(cdia/2,-0.140 , 0.0  ,"x",'z',-1.21,1.21)
    mypipes.add_pipe(cdia/2, 0.140 , 0.0  ,"x",'z',-1.21,1.21)

    mypipes.add_pipe(0.042/2,-0.20, 0.0,"x",'z',-1.21,1.21)
    mypipes.add_pipe(0.042/2, 0.20, 0.0,"x",'z',-1.21,1.21)
    
    #front wall feed throughs
    ctrdia = 0.040+rad_add*2#meter
    mypipes.add_pipe(ctrdia/2, 0.0   ,-0.140,"x",'z',1,1.21)
    mypipes.add_pipe(ctrdia/2, 0.0   , 0.140,"x",'z',1,1.21)
    mypipes.add_pipe(ctrdia/2,-0.140 , 0.0  ,"x",'z',1,1.21)
    mypipes.add_pipe(ctrdia/2, 0.140 , 0.0  ,"x",'z',1,1.21)
    
    #corner feed throughs
    cdia = 0.1016+rad_add*2#meter
    mypipes.add_pipe(cdia/2,-0.9 , 0.9 ,"x",'z',-1.21,1.21)
    mypipes.add_pipe(cdia/2, 0.9 , 0.9 ,"x",'z',-1.21,1.21)
    mypipes.add_pipe(cdia/2, 0.9 ,-0.9 ,"x",'z',-1.21,1.21)
    mypipes.add_pipe(cdia/2,-0.9 ,-0.9 ,"x",'z',-1.21,1.21)

    #----------------------------------------
    #side wall pipes
    #nominal feed through sizes,rad_add
    r3x5 =   0.001*(71+12.9)/2#m 71mm B0 form feed through, 2.9mm oversize
    rCorner= 0.001*(110+12.9)/2#m
    rHg199 = 0.001*(35+12.9)/2#m
    rpipes=[rCorner,           rCorner,
            rCorner,           rCorner,
            r3x5,r3x5,r3x5,r3x5,r3x5,
                  rHg199,rHg199,
            r3x5,r3x5,r3x5,r3x5,r3x5,
                  rHg199,rHg199,
            r3x5,r3x5,r3x5,r3x5,r3x5,
            rCorner,            rCorner,
            rCorner,           rCorner
            ] #meter
    ypipes=[1.050,            1.050,
            0.840,               0.840,
            -0.4,-0.4,-0.4,-0.4,-0.4,
                  0.14,0.185/2,
             0,   0,   0,   0,   0,
                  -0.14,-0.185/2,
             0.4, 0.4, 0.4, 0.4, 0.4,
            -0.840,             -0.840,
            -1.050,             -1.050,
            ] #meter
    zpipes=[-0.840,               0.840,
            -1.050,            1.050,
            -0.44,-0.20,0,0.20,0.44,
                       0,0,
            -0.44,-0.20,0,0.20,0.44,
                       0,0,
            -0.44,-0.20,0,0.20,0.44,
            -1.050,            1.050,
            -0.840,               0.840
            ] #meter
    
    rpipes = np.array(rpipes)
    print("rpipes = " , rpipes)
    for j in range(len(rpipes)):
        mypipes.add_pipe(rpipes[j]+rad_add,zpipes[j],ypipes[j],'y',"z",-1.21,1.21)
'''
