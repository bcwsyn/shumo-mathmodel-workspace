"""Cell-centered finite-volume check for the Q1 radial model."""
from __future__ import annotations
import numpy as np
from scipy.sparse import eye, lil_matrix
from scipy.sparse.linalg import spsolve
from openpyxl import load_workbook
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_air():
    wb = load_workbook(ROOT / "附件" / "附件1.xlsx", read_only=True, data_only=True)
    a = np.asarray(list(wb.active.iter_rows(min_row=2, values_only=True)), float)
    wb.close()
    return a[:, 0], a[:, 1], a[:, 2]


def harm(a, b):
    return 2*a*b/(a+b)


def assemble(dr, coeff, robin_h, air, cap):
    # Unknowns are cell-centre values at (i+1/2)dr. Boundary is a face.
    m = len(coeff)
    R = m*dr
    rf = np.arange(m+1)*dr
    A = lil_matrix((m, m), dtype=float)
    b = np.zeros(m)
    cf = harm(coeff[:-1], coeff[1:])
    # center cell: integral r dr = dr^2/2
    vol = dr*dr/2
    cp = rf[1]*cf[0]/dr
    A[0, 0] = -cp/(vol*cap); A[0, 1] = cp/(vol*cap)
    for i in range(1, m-1):
        vol = (i+0.5)*dr*dr
        cm = rf[i]*cf[i-1]/dr; cp = rf[i+1]*cf[i]/dr
        A[i, i-1] = cm/(vol*cap); A[i, i] = -(cm+cp)/(vol*cap); A[i, i+1] = cp/(vol*cap)
    # Outer face: eliminate the surface value using the half-cell resistance.
    vol = R*dr - dr*dr/2
    cm = rf[m-1]*cf[m-2]/dr
    d2 = dr/2
    c_surface = coeff[-1]
    beta = R*robin_h*c_surface/(c_surface + d2*robin_h)
    A[m-1, m-2] = cm/(vol*cap); A[m-1, m-1] = -(cm+beta)/(vol*cap); b[m-1] = beta*air/(vol*cap)
    return A, b


def surface_value(q_last, coeff_last, robin_h, air, dr):
    return (coeff_last*q_last + dr/2*robin_h*air)/(coeff_last + dr/2*robin_h)


def solve(dr_cm=0.05, dt=0.5, end=1800):
    at, aa, ac = read_air(); dr=dr_cm/100; m=int(round(.02/dr)); R=.02
    rho,cp,k,h,hm=820.,2600.,.36,25.,8e-7; cap=rho*cp; th=.5
    qT=np.full(m,28.); qC=np.full(m,2.55); I=eye(m,format='csc');
    At,_=assemble(dr,np.full(m,k),h,0.,cap); Lt=(I-th*dt*At.tocsc()).tocsc(); Rt=(I+(1-th)*dt*At.tocsc()).tocsc()
    nout=int(end); Tout=np.empty((nout,m)); Cout=np.empty((nout,m));
    steps=int(round(end/dt)); oldA=None; oldb=None
    for step in range(steps):
        t0=step*dt; t1=(step+1)*dt; ta0=float(np.interp(t0,at,aa)); ta1=float(np.interp(t1,at,aa)); ca0=float(np.interp(t0,at,ac)); ca1=float(np.interp(t1,at,ac))
        _,bt0=assemble(dr,np.full(m,k),h,ta0,cap); _,bt1=assemble(dr,np.full(m,k),h,ta1,cap)
        qT=np.asarray(spsolve(Lt,Rt@qT+dt*(th*bt1+(1-th)*bt0)))
        D=7e-9*np.exp(-.89/np.maximum(qC,1e-12)); oldA,oldb=assemble(dr,D,hm,ca0,1.)
        rhs=(I+(1-th)*dt*oldA.tocsc())@qC+dt*(1-th)*oldb; qi=qC.copy()
        for _ in range(40):
            Dn=7e-9*np.exp(-.89/np.maximum(qi,1e-12)); An,bn=assemble(dr,Dn,hm,ca1,1.); L=(I-th*dt*An.tocsc()).tocsc(); cand=np.asarray(spsolve(L,rhs+dt*th*bn)); upd=.7*cand+.3*qi
            if np.max(np.abs(upd-qi))<1e-12: qi=upd; break
            qi=upd
        qC=qi
        if (step+1)%int(round(1/dt))==0:
            j=(step+1)//int(round(1/dt))-1; Tout[j]=qT; Cout[j]=qC
    return np.arange(1,nout+1), np.arange(m)*dr+dr/2, Tout, Cout


def output_at(arr, centers, t, target_cm):
    # center value by quadratic even extension; surface value is handled outside.
    out=[]
    dr=centers[1]-centers[0]
    for xcm in target_cm:
        x=xcm/100
        if abs(x)<1e-15: out.append((9*arr[t-1,0]-arr[t-1,1])/8)
        elif abs(x-(centers[-1]+dr/2))<1e-12: out.append(arr[t-1,-1])
        else: out.append(np.interp(x,centers,arr[t-1]))
    return np.asarray(out)


if __name__=='__main__':
    target=[0,.5,1,1.5,2]
    t1,x1,T1,C1=solve(.05,.5); t2,x2,T2,C2=solve(.025,.25)
    ii=[v-1 for v in [100,300,600,900,1200,1500,1800]]
    # Surface is reconstructed from the last cell each time.
    def table(T,C,x,t):
        rowsT=[]; rowsC=[]
        for k in ii:
            bt=output_at(T,x,k+1,target[:-1]).tolist(); bc=output_at(C,x,k+1,target[:-1]).tolist()
            ts=surface_value(T[k,-1],.36,25,float(np.interp(k+1,t1,[28])),x[1]-x[0])
            # air value is only needed for the surface; use source interpolation below in final script
            rowsT.append(bt+[ts]); rowsC.append(bc+[surface_value(C[k,-1],7e-9*np.exp(-.89/max(C[k,-1],1e-12)),8e-7,float(np.interp(k+1,t1,[.02])),x[1]-x[0])])
        return rowsT,rowsC
    print('shapes',T1.shape,T2.shape)
    print('T_0.05_vs_0.025 interior',float(np.max(np.abs(T1[ii][:,::2]-T2[ii][:,::4]))))
