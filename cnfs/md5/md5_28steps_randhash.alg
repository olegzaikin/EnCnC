// Входной 512-битный блок текста, состоит из 32-битных подблоков
__in bit M[16][32];
__out bit Out[4][32];

// Инициализируем переменные сцепления, в них же накапливается результат
bit A[32] = 0x67452301;
bit B[32] = 0xEFCDAB89;
bit C[32] = 0x98BADCFE;
bit D[32] = 0x10325476;

// Random hash
bit H0[32] = 0x62c7Ec0c;
bit H1[32] = 0x751e497c;
bit H2[32] = 0xd49a54c1;
bit H3[32] = 0x2b76cff8;

// Нелинейные функции
bit F(bit X[32], bit Y[32], bit Z[32])
{
	return (X&Y)|(!X&Z);
}

bit G(bit X[32], bit Y[32], bit Z[32])
{
	return (X&Z)|(Y&!Z);
}

bit H(bit X[32], bit Y[32], bit Z[32])
{
	return X^Y^Z;
}

bit I(bit X[32], bit Y[32], bit Z[32])
{
	return Y^(X|!Z);
}

// @return b + ((a + F(b, c, d) + M + t) <<< s)
bit FF(bit a[32], bit b[32], bit c[32], bit d[32], bit M[32], int s, bit t[32])
{
	a = sum(sum(sum(a, F(b, c, d), 32), M, 32), t, 32);
	return b + (a <<< s);
}

// @return b + ((a + G(b, c, d) + M + t) <<< s)
bit GG(bit a[32], bit b[32], bit c[32], bit d[32], bit M[32], int s, bit t[32])
{
	a = sum(sum(sum(a, G(b, c, d), 32), M, 32), t, 32);
	return b + (a <<< s);
}

// @return b + ((a + H(b, c, d) + M + t) <<< s)
bit HH(bit a[32], bit b[32], bit c[32], bit d[32], bit M[32], int s, bit t[32])
{
	a = sum(sum(sum(a, H(b, c, d), 32), M, 32), t, 32);
	return b + (a <<< s);
}

// @return b + ((a + I(b, c, d) + M + t) <<< s)
bit II(bit a[32], bit b[32], bit c[32], bit d[32], bit M[32], int s, bit t[32])
{
	a = sum(sum(sum(a, I(b, c, d), 32), M, 32), t, 32);
	return b + (a <<< s);
}

void main()
{
	bit a[32] = A;
	bit b[32] = B;
	bit c[32] = C;
	bit d[32] = D;
	
	// Step 1: FF(a,b,c,d,M_j,s,t_j) означает a = b + ((a + F(b,c,d) + M[j] + t_j) <<< s)

	a = FF(a, b, c, d, M[0], 7, 0xd76aa478);
	d = FF(d, a, b, c, M[1], 12, 0xe8c7b756);
	c = FF(c, d, a, b, M[2], 17, 0x242070db);
	b = FF(b, c, d, a, M[3], 22, 0xc1bdceee);

	a = FF(a, b, c, d, M[4], 7, 0xf57c0faf);
	d = FF(d, a, b, c, M[5], 12, 0x4787c62a);
	c = FF(c, d, a, b, M[6], 17, 0xa8304613);
	b = FF(b, c, d, a, M[7], 22, 0xfd469501);
	
	a = FF(a, b, c, d, M[8], 7, 0x698098d8);
	d = FF(d, a, b, c, M[9], 12, 0x8b44f7af);
	c = FF(c, d, a, b, M[10], 17, 0xffff5bb1);
	b = FF(b, c, d, a, M[11], 22, 0x895cd7be);

	a = FF(a, b, c, d, M[12], 7, 0x6b901122);
	d = FF(d, a, b, c, M[13], 12, 0xfd987193);
	c = FF(c, d, a, b, M[14], 17, 0xa679438e);
	b = FF(b, c, d, a, M[15], 22, 0x49b40821);

	// Step 2: GG(a,b,c,d,M_j,s,t_j) означает a = b + ((a + G(b,c,d) + M[j] + t_j) <<< s)

	a = GG(a, b, c, d, M[1], 5, 0xf61e2562);
	d = GG(d, a, b, c, M[6], 9, 0xc040b340);
	c = GG(c, d, a, b, M[11], 14, 0x265e5a51);
	b = GG(b, c, d, a, M[0], 20, 0xe9b6c7aa);

	a = GG(a, b, c, d, M[5], 5, 0xd62f105d);
        d = GG(d, a, b, c, M[10], 9, 0x02441453);
	c = GG(c, d, a, b, M[15], 14, 0xd8a1e681);
	b = GG(b, c, d, a, M[4], 20, 0xe7d3fbc8);

	a = GG(a, b, c, d, M[9], 5, 0x21e1cde6);
	d = GG(d, a, b, c, M[14], 9, 0xc33707d6);
	c = GG(c, d, a, b, M[3], 14, 0xf4d50d87);
	b = GG(b, c, d, a, M[8], 20, 0x455a14ed);

	Out[0] = a;
	Out[1] = b;
	Out[2] = c;
	Out[3] = d;

	assert(!(Out[0] ^ H0));
        assert(!(Out[1] ^ H1));
	assert(!(Out[2] ^ H2));
	assert(!(Out[3] ^ H3));
}
