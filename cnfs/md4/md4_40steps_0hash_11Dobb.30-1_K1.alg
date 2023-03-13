__in bit M[16][32];
bit K[32] = 0xFFFFFFFF;
__out bit Hash[4][40];

bit A[32] = 0x67452301;
bit B[32] = 0xEFCDAB89;
bit C[32] = 0x98BADCFE;
bit D[32] = 0x10325476;


bit F(bit X[32], bit Y[32], bit Z[32])
{
    return (X&Y)|(!X&Z);
}

bit G(bit X[32], bit Y[32], bit Z[32])
{
    return X&Y | X&Z | Y&Z;
}

bit H(bit X[32], bit Y[32], bit Z[32])
{
    return X^Y^Z;
}

// Round 1, (a + F(b, c, d) + M) <<< s
bit FF(bit a[32], bit b[32], bit c[32], bit d[32], bit M[32], int s)
{
    a = sum(sum(a, F(b, c, d), 32), M, 32);
    return (a <<< s);
}

// Round 2, (a + G(b, c, d) + M + 0x5A827999) <<< s
bit GG(bit a[32], bit b[32], bit c[32], bit d[32], bit M[32], int s)
{
    a = sum(sum(sum(a, G(b, c, d), 32), M, 32), 0x5A827999, 32);
    return (a <<< s);
}

// Round 3, (a + H(b, c, d) + M + 0x6ED9EBA1) <<< s
bit HH(bit a[32], bit b[32], bit c[32], bit d[32], bit M[32], int s)
{
    a = sum(sum(sum(a, H(b, c, d), 32), M, 32), 0x6ED9EBA1, 32);
    return (a <<< s);
}



void main()
{

    bit a[32] = A;
    bit b[32] = B;
    bit c[32] = C;
    bit d[32] = D;
    
    // Round 1: steps 1--16

    a = FF(a, b, c, d, M[0], 3);
    d = FF(d, a, b, c, M[1], 7);
    c = FF(c, d, a, b, M[2], 11);
    b = FF(b, c, d, a, M[3], 19);

    a = FF(a, b, c, d, M[4], 3);
    d = FF(d, a, b, c, M[5], 7);
    c = FF(c, d, a, b, M[6], 11);
    b = FF(b, c, d, a, M[7], 19);
    
    a = FF(a, b, c, d, M[8], 3);
    d = FF(d, a, b, c, M[9], 7);
    c = FF(c, d, a, b, M[10], 11);
    b = FF(b, c, d, a, M[11], 19);

    a = FF(a, b, c, d, M[12], 3);
    assert(a[0]);
    assert(a[1]);
    assert(a[2]);
    assert(a[3]);
    assert(a[4]);
    assert(a[5]);
    assert(a[6]);
    assert(a[7]);
    assert(a[8]);
    assert(a[9]);
    assert(a[10]);
    assert(a[11]);
    assert(a[12]);
    assert(a[13]);
    assert(a[14]);
    assert(a[15]);
    assert(a[16]);
    assert(a[17]);
    assert(a[18]);
    assert(a[19]);
    assert(a[20]);
    assert(a[21]);
    assert(a[22]);
    assert(a[23]);
    assert(a[24]);
    assert(a[25]);
    assert(a[26]);
    assert(a[27]);
    assert(a[28]);
    assert(a[29]);
    assert(!a[30]);
    assert(a[31]);
    d = FF(d, a, b, c, M[13], 7); assert(!(d ^ K)); // constraint: Q[14] = K
    c = FF(c, d, a, b, M[14], 11); assert(!(c ^ K)); // constraint: Q[15] = K
    b = FF(b, c, d, a, M[15], 19);

    // Round 2: steps 17--32
    a = GG(a, b, c, d, M[0], 3); assert(!(a ^ K)); // constraint: Q[17] = K
    d = GG(d, a, b, c, M[4], 5); assert(!(d ^ K)); // constraint: Q[18] = K
    c = GG(c, d, a, b, M[8], 9); assert(!(c ^ K)); // constraint: Q[19] = K
    b = GG(b, c, d, a, M[12], 13);


    a = GG(a, b, c, d, M[1], 3); assert(!(a ^ K)); // constraint: Q[21] = K
    d = GG(d, a, b, c, M[5], 5); assert(!(d ^ K)); // constraint: Q[22] = K
    c = GG(c, d, a, b, M[9], 9); assert(!(c ^ K)); // constraint: Q[23] = K
    b = GG(b, c, d, a, M[13], 13);

    a = GG(a, b, c, d, M[2], 3); assert(!(a ^ K)); // constraint: Q[25] = K
    d = GG(d, a, b, c, M[6], 5); assert(!(d ^ K)); // constraint: Q[26] = K
    c = GG(c, d, a, b, M[10], 9); assert(!(c ^ K)); // constraint: Q[27] = K
    b = GG(b, c, d, a, M[14], 13);

    a = GG(a, b, c, d, M[3], 3);
    d = GG(d, a, b, c, M[7], 5);
    c = GG(c, d, a, b, M[11], 9);
    b = GG(b, c, d, a, M[15], 13);
	
    // Round 3: Steps 33-40

    a = HH(a, b, c, d, M[0], 3);
    d = HH(d, a, b, c, M[8], 9);
    c = HH(c, d, a, b, M[4], 11);
    b = HH(b, c, d, a, M[12], 15);

    a = HH(a, b, c, d, M[2], 3);
    d = HH(d, a, b, c, M[10], 9);
    c = HH(c, d, a, b, M[6], 11);
    b = HH(b, c, d, a, M[14], 15);

    // Round 3: Steps 41-48

    Hash[0] = a;
    Hash[1] = b;
    Hash[2] = c;
    Hash[3] = d;

    // the 128-bit hash value is fixed with zero:
    assert (!Hash[0]);
    assert (!Hash[1]);
    assert (!Hash[2]);
    assert (!Hash[3]);

}
