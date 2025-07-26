/*****************************************************************************
 * clock.h: clocks synchronisation
 *****************************************************************************
 * Copyright (C) 2008 the VideoLAN team
 * Copyright (C) 2008 Laurent Aimar
 * $Id: 33e0b86230f1c7f39376a043f20ff85db58656a1 $
 *
 * Authors: Laurent Aimar < fenrir _AT_ videolan _DOT_ org >
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston MA 02110-1301, USA.
 *****************************************************************************/

#if defined(__PLUGIN__) || defined(__BUILTIN__) || !defined(__LIBVLC__)
# error This header file can only be included from LibVLC.
#endif

#ifndef _INPUT_CLOCK_H
#define _INPUT_CLOCK_H 1

#include <vlc_common.h>

typedef struct input_clock_t input_clock_t;

input_clock_t *input_clock_New( bool b_master, int i_cr_average, int i_rate );
void           input_clock_Delete( input_clock_t * );

void    input_clock_SetPCR( input_clock_t *, vlc_object_t *p_log,
                            bool b_can_pace_control, mtime_t i_clock, mtime_t i_system );
void    input_clock_ResetPCR( input_clock_t * );
mtime_t input_clock_GetTS( input_clock_t *, mtime_t i_pts_delay, mtime_t );
void    input_clock_SetRate( input_clock_t *cl, int i_rate );
void    input_clock_SetMaster( input_clock_t *cl, bool b_master );
mtime_t input_clock_GetWakeup( input_clock_t *cl );

#endif

