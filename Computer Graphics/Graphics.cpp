#include <stdio.h>
#include <graphics.h>
#include <conio.h>
#include <stdlib.h>

int main()
{
    int x1, y1, x2, y2;
    int dx, dy, sx, sy, err, e2;

    printf("Enter 1st point: ");
    scanf("%d%d", &x1, &y1);

    printf("Enter 2nd point: ");
    scanf("%d%d", &x2, &y2);

    // WinBGIm
    int gd = 0, gm = 0;

    initgraph(&gd, &gm, " ");

    dx = abs(x2 - x1);
    dy = abs(y2 - y1);

    sx = (x1 < x2) ? 1 : -1;
    sy = (y1 < y2) ? 1 : -1;

    err = dx - dy;

    while (1)
    {
        putpixel(x1, y1, WHITE);

        if (x1 == x2 && y1 == y2)
            break;

        e2 = 2 * err;

        if (e2 > -dy)
        {
            err = err - dy;
            x1 = x1 + sx;
        }

        if (e2 < dx)
        {
            err = err + dx;
            y1 = y1 + sy;
        }
    }

    getch();
    closegraph();

    return 0;
}