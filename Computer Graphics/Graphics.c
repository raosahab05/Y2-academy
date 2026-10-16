#include<stdio.h>
#include<conio.h>
#include<graphics.h>

int main()
{
    int x,y,x1,y1,x2,y2,i,dx,dy,P:

int gd = DETECT,gm;

printf("Enter 1st points");

Scanf("%d%d", &x1, &y1);

printf("Enter 2nd points");

Scanf("%d%d",&x2, &y2);

int graph (&gd, &gm);

Or

/* intgraph &gd &sm, (char * " "); */

dx = x2-x1;

dy = y2-y1;

P = 2*dy -dx

n = x;
y = y;

i=0;

While (i<dx)
{ 
if (P<0)
{
x = x+1;
P = P+2*dy;
}
else
{
x = x+1;
y = y+1;
P = P+2*dy-2*dx;
}
i= i+1;
}
getch();
closegraph();
return 0;
}